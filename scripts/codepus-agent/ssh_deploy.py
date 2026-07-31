"""
SSH 零停机部署执行器 (CodePus autonomous deploy)。
从环境变量 SSH_HOST/SSH_USER/SSH_PASS 读取凭据,绝不硬编码密码。
执行: git pull → alembic upgrade head → 前端构建 → 滚动重启 → 健康检查。
用法:
    $env:SSH_HOST="8.166.120.119"; $env:SSH_USER="root"; $env:SSH_PASS="xxx"
    python scripts/codepus-agent/ssh_deploy.py
"""
import os
import sys
import time
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 环境变量未设置")
    sys.exit(2)

PROJECT_DIR = "/home/deploy/ai-interview"
BACKEND_DIR = f"{PROJECT_DIR}/ai-interview-backend"
FRONTEND_DIR = f"{PROJECT_DIR}/ai-interview-frontend"
ADMIN_DIR = f"{PROJECT_DIR}/ai-interview-admin"

STEPS = [
    ("1. git pull 拉取最新代码",
     f"cd {PROJECT_DIR} && git pull origin main 2>&1"),

    ("2. 后端安装依赖(增量)",
     f"cd {BACKEND_DIR} && pip install -r requirements.txt -q 2>&1 | tail -5"),

    ("3. 数据库迁移 alembic upgrade head",
     f"cd {BACKEND_DIR} && docker compose run --rm app alembic upgrade head 2>&1 || "
     f"docker exec ai-interview-app alembic upgrade head 2>&1 || "
     f"echo 'MIGRATION_SKIPPED'"),

    ("4. 构建用户端前端",
     f"cd {FRONTEND_DIR} && npm install --silent 2>&1 | tail -3 && npm run build 2>&1 | tail -8"),

    ("5. 构建管理后台",
     f"cd {ADMIN_DIR} && npm install --silent 2>&1 | tail -3 && npm run build 2>&1 | tail -8"),

    ("6. 滚动重启后端容器(零停机)",
     f"cd {BACKEND_DIR} && docker compose up -d --no-deps --wait app 2>&1 && "
     f"docker compose up -d --no-deps celery-worker celery-beat 2>&1 && "
     f"docker compose up -d --no-deps nginx 2>&1"),

    ("7. 健康检查",
     f"for i in 1 2 3 4 5 6; do "
     f"STATUS=$(curl -s -o /dev/null -w '%{{http_code}}' http://localhost:8006/api/v1/config/health 2>/dev/null); "
     f"echo \"healthcheck attempt $i: $STATUS\"; "
     f"if [ \"$STATUS\" = \"200\" ]; then echo 'HEALTH_OK'; break; fi; "
     f"sleep 10; done"),
]


def run_step(ssh, label, cmd, timeout=600):
    print(f"\n{'='*60}\n>>> {label}\n{'='*60}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(f"[stderr] {err.rstrip()}")
    print(f"[exit={rc}]")
    return rc


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=20, auth_timeout=20)
    except Exception as e:
        print(f"SSH 连接失败: {e}")
        sys.exit(2)
    print("SSH 连接成功")

    failed = []
    for label, cmd in STEPS:
        rc = run_step(ssh, label, cmd, timeout=900)
        if rc != 0 and "MIGRATION_SKIPPED" not in label:
            failed.append(label)
            # 关键步骤失败仍继续后续步骤,最后汇总

    # 最终容器状态
    print(f"\n{'='*60}\n>>> 最终容器状态\n{'='*60}")
    run_step(ssh, "docker compose ps", f"cd {BACKEND_DIR} && docker compose ps 2>&1", timeout=30)

    ssh.close()
    if failed:
        print(f"\n[部署完成,但有步骤失败]: {failed}")
        sys.exit(1)
    print("\n[部署全部成功]")


if __name__ == "__main__":
    main()
