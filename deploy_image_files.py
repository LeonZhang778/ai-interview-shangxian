"""Deploy image task files to both app and celery-worker containers on the server."""
import paramiko
import os
import time

SERVER = os.environ.get("DEPLOY_SSH_HOST", "8.166.120.119")
USER = os.environ.get("DEPLOY_SSH_USER", "root")
# 服务器凭据从环境变量读取（历史上此文件硬编码 root 口令并已提交，属凭据泄露）
PASS = os.environ.get("DEPLOY_SSH_PASS")
if not PASS:
    raise SystemExit("缺少环境变量 DEPLOY_SSH_PASS（服务器 SSH 口令），请显式设置后再运行。")

LOCAL_BASE = "D:/ai-interview/ai-interview-backend"

FILES = [
    "app/models/image_task.py",
    "app/schemas/client/image.py",
    "app/services/client/image_service.py",
    "app/schedule/jobs/image_task.py",
    "app/api/client/v1/image.py",
    "app/models/__init__.py",
    "app/core/celery_app.py",
    "app/route/router_registry.py",
]

CONTAINERS = ["ai-interview-app", "ai-interview-celery-worker"]


def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASS)
    return ssh


def upload_and_copy(ssh, local_path, remote_path, container):
    """Upload file via SFTP then docker cp to container."""
    filename = os.path.basename(local_path)
    tmp_path = f"/tmp/{filename}"

    sftp = ssh.open_sftp()
    sftp.put(local_path, tmp_path)
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command(f"docker cp {tmp_path} {container}:{remote_path}")
    stdout.read()
    err = stderr.read().decode().strip()

    ssh.exec_command(f"rm -f {tmp_path}")
    return err


def main():
    ssh = connect()

    # Ensure directories exist
    dirs = [
        "/app/app/schedule/jobs",
        "/app/app/schemas/client",
        "/app/app/services/client",
        "/app/app/api/client/v1",
    ]
    for d in dirs:
        for container in CONTAINERS:
            ssh.exec_command(f"docker exec {container} mkdir -p {d}")

    for rel_path in FILES:
        local_path = os.path.join(LOCAL_BASE, rel_path.replace("/", os.sep))
        container_dest = f"/app/{rel_path}"

        for container in CONTAINERS:
            try:
                err = upload_and_copy(ssh, local_path, container_dest, container)
                if err:
                    print(f"  ERROR: {container}:{container_dest}: {err}")
                else:
                    print(f"  OK: {container}:{container_dest}")
            except Exception as e:
                print(f"  Reconnecting after error: {e}")
                ssh.close()
                time.sleep(1)
                ssh = connect()
                try:
                    err = upload_and_copy(ssh, local_path, container_dest, container)
                    if err:
                        print(f"  ERROR (retry): {container}:{container_dest}: {err}")
                    else:
                        print(f"  OK (retry): {container}:{container_dest}")
                except Exception as e2:
                    print(f"  FAILED (retry): {container}:{container_dest}: {e2}")

    # Verify
    for container in CONTAINERS:
        stdin, stdout, stderr = ssh.exec_command(
            f"docker exec {container} ls -la /app/app/models/image_task.py /app/app/schedule/jobs/image_task.py /app/app/services/client/image_service.py 2>&1"
        )
        print(f"\n=== {container} verify ===")
        print(stdout.read().decode())

    ssh.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
