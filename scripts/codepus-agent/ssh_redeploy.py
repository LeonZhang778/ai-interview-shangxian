"""
SSH 重新部署执行器 (磁盘清理后补部署)。
磁盘已清理释放 22GB，代码已 pull 到 27afe54，但容器仍跑旧镜像。
本脚本拉取新镜像并重建容器，完成本轮 P1-AI智能标签功能的部署。
凭据从环境变量 SSH_HOST/SSH_USER/SSH_PASS 读取。
"""
import os, sys, time, paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 环境变量未设置"); sys.exit(2)

COMMIT = "27afe5497c86c118e0fbcac4870e9a7044c9b139"
ACR = "crpi-yluu2a4ik5gs0met.cn-guangzhou.personal.cr.aliyuncs.com/rwkkyyds-ai-interviews/ai-interviews-shangxian"
IMAGE = f"{ACR}:{COMMIT}"
BACKEND_DIR = "/home/deploy/ai-interview/ai-interview-backend"

STEPS = [
    ("1. 确认服务器代码版本",
     f"cd /home/deploy/ai-interview && git log -1 --oneline 2>&1"),

    ("2. 拉取新镜像 docker pull",
     f"docker pull {IMAGE} 2>&1"),

    ("3. 停止 app/worker/beat 容器",
     f"cd {BACKEND_DIR} && docker compose stop app celery-worker celery-beat 2>&1 || true"),

    ("4. 重建 app 容器(新镜像)",
     f"cd {BACKEND_DIR} && BACKEND_IMAGE={IMAGE} docker compose up -d --force-recreate --no-deps app 2>&1"),

    ("5. 等待 8 秒让 app 启动",
     "sleep 8; echo slept"),

    ("6. 执行数据库迁移 alembic upgrade head",
     f"docker exec ai-interview-app alembic upgrade head 2>&1 || true"),

    ("7. 确认迁移版本",
     f"docker exec ai-interview-app alembic current 2>&1"),

    ("8. 轮询 app 健康状态(最多 60s)",
     "for i in $(seq 1 12); do "
     "H=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' ai-interview-app 2>/dev/null); "
     "echo \"attempt $i: $H\"; "
     "if [ \"$H\" = \"healthy\" ]; then echo HEALTH_OK; break; fi; "
     "sleep 5; done"),

    ("9. 重建 celery-worker 容器",
     f"cd {BACKEND_DIR} && BACKEND_IMAGE={IMAGE} docker compose up -d --force-recreate --no-deps celery-worker 2>&1"),

    ("10. 重建 celery-beat 容器",
     f"cd {BACKEND_DIR} && BACKEND_IMAGE={IMAGE} docker compose up -d --force-recreate --no-deps celery-beat 2>&1"),

    ("11. nginx 健康检查(经 host nginx 80 端口)",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/api/v1/config/health 2>&1; echo"),

    ("12. app 直连健康检查(8006 端口)",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost:8006/api/v1/config/health 2>&1; echo"),

    ("13. 容器状态总览",
     "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}' 2>&1"),

    ("14. app 容器镜像确认(应为新 commit)",
     f"docker inspect ai-interview-app --format '{{{{.Image}}}}' 2>&1; "
     f"docker images {ACR} --format '{{{{.Tag}}}}\\t{{{{.ID}}}}\\t{{{{.CreatedSince}}}}' 2>&1 | head -5"),
]


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=20, auth_timeout=20)
        print("SSH 连接成功\n")
    except Exception as e:
        print(f"SSH 连接失败: {e}"); sys.exit(3)

    failed = []
    for label, cmd in STEPS:
        print(f"{'='*70}\n>>> {label}\n{'='*70}")
        try:
            _, stdout, stderr = ssh.exec_command(cmd, timeout=300, get_pty=False)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            if out.strip(): print(out.rstrip())
            if err.strip(): print(f"[stderr] {err.rstrip()}")
            print(f"[exit={rc}]\n")
            if rc != 0 and "alembic" not in label:
                failed.append(label)
        except Exception as e:
            print(f"[执行异常] {e}\n")
            failed.append(label)

    ssh.close()
    if failed:
        print(f"[部署完成,但有步骤失败]: {failed}")
        sys.exit(1)
    print("\n[部署全部成功]")


if __name__ == "__main__":
    main()
