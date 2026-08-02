"""通过 SSH 诊断并在必要时为低内存服务器启用单 worker。"""
from __future__ import annotations

import base64
import os
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
SSH_PASS = os.environ.get("SSH_PASS", "")

DIAGNOSE_SCRIPT = r'''set -Eeuo pipefail
cd /home/deploy/ai-interview/ai-interview-backend
printf '%s\n' '--- host memory ---'
free -h || true
printf '%s\n' '--- host load ---'
uptime || true
printf '%s\n' '--- app state ---'
docker inspect --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{.State.Error}} started={{.State.StartedAt}}' ai-interview-app || true
printf '%s\n' '--- app stats ---'
docker stats --no-stream ai-interview-app ai-interview-postgres ai-interview-redis || true
printf '%s\n' '--- app inspect ---'
docker inspect --format 'path={{.Path}} args={{json .Args}} env={{range .Config.Env}}{{if or (eq (index (split . "=") 0) "API_PORT") (eq (index (split . "=") 0) "ENV")}}{{.}} {{end}}{{end}}' ai-interview-app || true
printf '%s\n' '--- app probes ---'
for port in 8001 8006; do
    docker exec ai-interview-app python -c "import urllib.request; response=urllib.request.urlopen('http://127.0.0.1:${port}/api/v1/config/health', timeout=3); print(${port}, response.status, response.read().decode('utf-8', errors='replace')[:500])" 2>&1 || true
done
printf '%s\n' '--- app config ---'
docker exec ai-interview-app python -c "from app.core.config import settings; print('API_V1_STR='+repr(settings.API_V1_STR)); print('API_PORT='+repr(settings.API_PORT)); print('ENV='+repr(settings.ENV))" 2>&1 || true

docker inspect --format '{{json .State.Health}}' ai-interview-app || true
printf '%s\n' '--- tcp table ---'
docker exec ai-interview-app sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null || true' 2>&1 || true

docker logs --timestamps ai-interview-app --tail 120 2>&1 || true
'''


APPLY_SCRIPT = r'''set -Eeuo pipefail
cd /home/deploy/ai-interview/ai-interview-backend
printf '%s\n' '--- repair env line endings ---'
cp -p .env "/tmp/ai-interview-env-backup-$(date +%Y%m%d%H%M%S)"
perl -0pi -e 's/\\n/\n/g' .env
printf 'env_lines='; wc -l < .env
cat >/tmp/ai-interview-low-memory-override.yml <<'YAML'
services:
  app:
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8006 --workers 1
YAML
printf '%s\n' '--- validate override ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f /tmp/ai-interview-low-memory-override.yml config >/tmp/ai-interview-effective-compose.yml
printf '%s\n' '--- recreate app with one worker ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f /tmp/ai-interview-low-memory-override.yml up -d --force-recreate --no-deps app
for i in $(seq 1 36); do
    app_status=$(docker inspect --format='{{.State.Status}}' ai-interview-app 2>/dev/null || echo missing)
    health_status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' ai-interview-app 2>/dev/null || echo missing)
    if [ "$health_status" = healthy ]; then
        break
    fi
    printf 'Waiting for app (%s/36): status=%s health=%s\n' "$i" "$app_status" "$health_status"
    sleep 5
done
test "$(docker inspect --format='{{.State.Status}}' ai-interview-app)" = running
test "$(docker inspect --format='{{.State.Health.Status}}' ai-interview-app)" = healthy
printf '%s\n' '--- direct health ---'
docker exec ai-interview-app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=10).status)" | grep -qx 200
printf '%s\n' '--- start celery services ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f /tmp/ai-interview-low-memory-override.yml up -d --force-recreate --no-deps celery-worker celery-beat
printf '%s\n' '--- final status ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f /tmp/ai-interview-low-memory-override.yml ps
'''


VERIFY_SCRIPT = r'''set -Eeuo pipefail
cd /home/deploy/ai-interview/ai-interview-backend
printf '%s\n' '--- compose config ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
printf '%s\n' 'compose=ok'
printf '%s\n' '--- app health ---'
curl -fsS http://localhost:8006/api/v1/config/health
printf '\n%s\n' '--- nginx health ---'
curl -fsS http://localhost:8080/health
printf '\n%s\n' '--- celery ping ---'
docker exec ai-interview-celery-worker celery -A app.core.celery_app inspect ping --timeout=5
printf '%s\n' '--- services ---'
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
'''


def run_remote(script: str) -> int:
    if not SSH_PASS:
        print("ERROR: SSH_PASS 未设置")
        return 2
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {USER}@{HOST} ...")
        client.connect(HOST, username=USER, password=SSH_PASS, timeout=20)
        encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
        _, stdout, stderr = client.exec_command(f"echo {encoded} | base64 -d | bash", timeout=300)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        if output:
            print(output.rstrip())
        if error:
            print(f"[stderr] {error.rstrip()}")
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


def main() -> int:
    mode = os.sys.argv[1] if len(os.sys.argv) > 1 else "diagnose"
    if mode == "diagnose":
        return run_remote(DIAGNOSE_SCRIPT)
    if mode == "apply":
        return run_remote(APPLY_SCRIPT)
    if mode == "verify":
        return run_remote(VERIFY_SCRIPT)
    print("用法: diagnose、apply 或 verify")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
