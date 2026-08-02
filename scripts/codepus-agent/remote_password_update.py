"""
远程同步 AI-Interview 服务器的 PostgreSQL / Redis 凭据。
凭据只从环境变量读取，不写入仓库，也不打印真实值。
"""
from __future__ import annotations

import base64
import os
import sys

import paramiko


HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
SSH_PASS = os.environ.get("SSH_PASS", "")
NEW_PASSWORD = os.environ.get("DB_REDIS_PASSWORD", "")


INSPECT_SCRIPT = r'''set -Eeuo pipefail
cd /home/deploy/ai-interview/ai-interview-backend
printf '%s\n' '--- containers ---'
docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'
printf '%s\n' '--- env keys ---'
if [ -f .env ]; then
  grep -E '^(POSTGRES_USER|POSTGRES_DB|POSTGRES_HOST|POSTGRES_PORT|REDIS_HOST|REDIS_PORT|API_PORT)=' .env | sed -E 's/=.*/=<configured>/' || true
  printf 'env_file=present\n'
else
  printf 'env_file=missing\n'
fi
printf '%s\n' '--- compose files ---'
ls -1 docker-compose*.yml 2>/dev/null || true
printf '%s\n' '--- postgres roles ---'
docker exec ai-interview-postgres psql -U postgres -d postgres -Atc "SELECT rolname FROM pg_roles WHERE rolcanlogin ORDER BY rolname;"
printf '%s\n' '--- container env keys ---'
for container_name in ai-interview-postgres ai-interview-redis ai-interview-app; do
  printf '%s: ' "$container_name"
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container_name" 2>/dev/null | sed -E 's/=.*$/=<configured>/' | tr '\n' ' ' || true
  printf '\n'
done
printf '%s\n' '--- redis command shape ---'
redis_cmd=$(docker inspect --format '{{join .Config.Cmd " "}}' ai-interview-redis 2>/dev/null || true)
if printf '%s' "$redis_cmd" | grep -q -- '--requirepass'; then
  echo 'redis_requirepass=configured'
else
  echo 'redis_requirepass=not_detected'
fi
printf '%s\n' '--- env file size ---'
wc -c .env 2>/dev/null || true
printf '%s\n' '--- postgres databases ---'
docker exec ai-interview-postgres psql -U postgres -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
printf '%s\n' '--- data volumes ---'
docker inspect --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}' ai-interview-postgres
docker inspect --format '{{range .Mounts}}{{println .Name .Destination}}{{end}}' ai-interview-redis
'''


DIAGNOSE_SCRIPT = r'''set -Eeuo pipefail
cd /home/deploy/ai-interview/ai-interview-backend
printf '%s\n' '--- container status ---'
docker compose ps || true
printf '%s\n' '--- app inspect ---'
docker inspect --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} exit={{.State.ExitCode}}' ai-interview-app || true
docker inspect --format '{{range .State.Health.Log}}{{println .Start "exit=" .ExitCode .Output}}{{end}}' ai-interview-app 2>/dev/null | tail -10 || true
printf '%s\n' '--- app logs ---'
docker logs ai-interview-app --tail 120 2>&1 || true
printf '%s\n' '--- direct health probes ---'
docker exec ai-interview-app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=5).status)" 2>&1 || true
curl -sS -i --max-time 10 http://127.0.0.1:8006/api/v1/config/health 2>&1 || true
printf '%s\n' '--- effective env keys ---'
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' ai-interview-app | grep -E '^(ENV|API_PORT|POSTGRES_USER|POSTGRES_DB|POSTGRES_HOST|POSTGRES_PORT|REDIS_HOST|REDIS_PORT|REDIS_PASSWORD)=' | sed -E 's/=.*$/=<configured>/' || true
printf '%s\n' '--- app command ---'
docker inspect --format 'entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}}' ai-interview-app || true
printf '%s\n' '--- import test ---'
docker exec ai-interview-app python -c "import main; print('import_main=ok')" 2>&1 || true
docker exec ai-interview-app python -c "from app.core.config import settings; print('config_load=ok ENV='+str(settings.ENV)+' API_PORT='+str(settings.API_PORT)+' POSTGRES_USER='+str(settings.POSTGRES_USER)+' POSTGRES_DB='+str(settings.POSTGRES_DB))" 2>&1 || true
printf '%s\n' '--- single-worker probe ---'
docker exec ai-interview-app sh -c "timeout 90s python -m uvicorn main:app --host 127.0.0.1 --port 8007 --workers 1" 2>&1 || true
printf '%s\n' '--- startup stack probe ---'
docker exec ai-interview-app sh -c "timeout 35s python -c \"import faulthandler; faulthandler.dump_traceback_later(15, repeat=False); import uvicorn; uvicorn.run('main:app', host='127.0.0.1', port=8007, workers=1)\"" 2>&1 || true
'''


APPLY_SCRIPT = r'''set -Eeuo pipefail

new_password=$(printf '%s' '__PASSWORD_B64__' | base64 -d)
export NEW_PASSWORD="$new_password"

timestamp=$(date +%Y%m%d%H%M%S)
backup_dir="/home/deploy/ai-interview/backups"
mkdir -p "$backup_dir"
umask 077

printf '%s\n' '--- preflight ---'
test -f .env
test -f docker-compose.yml
test -f docker-compose.prod.yml
docker inspect ai-interview-postgres >/dev/null
docker inspect ai-interview-redis >/dev/null

printf '%s\n' '--- backup PostgreSQL ---'
docker exec ai-interview-postgres pg_dump -U postgres -d postgres -Fc > "$backup_dir/postgres-$timestamp.dump"
test -s "$backup_dir/postgres-$timestamp.dump"
chmod 600 "$backup_dir/postgres-$timestamp.dump"

printf '%s\n' '--- backup .env ---'
cp -p .env "$backup_dir/env-$timestamp.backup"
chmod 600 "$backup_dir/env-$timestamp.backup"

printf '%s\n' '--- update PostgreSQL role password ---'
escaped_password=$(printf '%s' "$new_password" | sed "s/'/''/g")
export PGPASSWORD="$new_password"
printf "ALTER ROLE postgres PASSWORD '%s';\n" "$escaped_password" | docker exec -i -e PGPASSWORD="$new_password" ai-interview-postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1

printf '%s\n' '--- update .env ---'
NEW_PASSWORD="$new_password" python3 - <<'PY'
import os
import re
from pathlib import Path

path = Path('.env')
existing = path.read_text(encoding='utf-8')
values = {
    'ENV': 'production',
    'POSTGRES_USER': 'postgres',
    'POSTGRES_PASSWORD': os.environ['NEW_PASSWORD'],
    'POSTGRES_HOST': 'postgres',
    'POSTGRES_PORT': '5432',
    'POSTGRES_DB': 'postgres',
    'REDIS_HOST': 'redis',
    'REDIS_PORT': '6379',
    'REDIS_PASSWORD': os.environ['NEW_PASSWORD'],
}
lines = []
seen = set()
assignment = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=')
for line in existing.splitlines():
    match = assignment.match(line)
    key = match.group(1) if match else None
    if key in values:
        lines.append(f'{key}={values[key]}')
        seen.add(key)
    else:
        lines.append(line)
for key, value in values.items():
    if key not in seen:
        lines.append(f'{key}={value}')
path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
PY
chmod 600 .env

printf '%s\n' '--- validate compose config ---'
docker compose config >/tmp/ai-interview-compose-password-update.yml
grep -q 'POSTGRES_USER: postgres' /tmp/ai-interview-compose-password-update.yml
grep -q 'POSTGRES_DB: postgres' /tmp/ai-interview-compose-password-update.yml

printf '%s\n' '--- recreate PostgreSQL and Redis ---'
docker compose up -d --force-recreate postgres redis
for i in $(seq 1 30); do
    postgres_status=$(docker inspect --format='{{.State.Health.Status}}' ai-interview-postgres 2>/dev/null || echo missing)
    redis_status=$(docker inspect --format='{{.State.Health.Status}}' ai-interview-redis 2>/dev/null || echo missing)
    if [ "$postgres_status" = healthy ] && [ "$redis_status" = healthy ]; then
        break
    fi
    printf 'Waiting for database services (%s/30): postgres=%s redis=%s\n' "$i" "$postgres_status" "$redis_status"
    sleep 5
done
test "$(docker inspect --format='{{.State.Health.Status}}' ai-interview-postgres)" = healthy
test "$(docker inspect --format='{{.State.Health.Status}}' ai-interview-redis)" = healthy

printf '%s\n' '--- verify database authentication ---'
docker exec -e PGPASSWORD="$new_password" ai-interview-postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -Atc 'SELECT 1;' | grep -qx '1'
printf '%s\n' 'postgres_auth=ok'
printf '%s\n' '--- verify Redis authentication ---'
docker exec ai-interview-redis redis-cli -a "$new_password" --no-auth-warning ping | grep -qx PONG
printf '%s\n' 'redis_auth=ok'

printf '%s\n' '--- recreate application services ---'
docker compose up -d --force-recreate --no-deps app celery-worker celery-beat

printf '%s\n' '--- final status ---'
docker compose ps
'''


def run_remote(script: str, timeout: int = 600) -> int:
    if not SSH_PASS:
        print("ERROR: SSH_PASS 未设置", file=sys.stderr)
        return 2
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"Connecting to {USER}@{HOST} ...")
        client.connect(HOST, username=USER, password=SSH_PASS, timeout=20)
        encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
        command = f"echo {encoded} | base64 -d | bash"
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
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
    mode = sys.argv[1] if len(sys.argv) > 1 else "inspect"
    if mode == "inspect":
        return run_remote(INSPECT_SCRIPT, timeout=120)
    if mode == "diagnose":
        return run_remote(DIAGNOSE_SCRIPT, timeout=180)
    if mode == "apply":
        if not NEW_PASSWORD:
            print("ERROR: DB_REDIS_PASSWORD 未设置", file=sys.stderr)
            return 2
        encoded_password = base64.b64encode(NEW_PASSWORD.encode("utf-8")).decode("ascii")
        return run_remote(APPLY_SCRIPT.replace("__PASSWORD_B64__", encoded_password))
    print("用法: inspect、diagnose 或 apply", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
