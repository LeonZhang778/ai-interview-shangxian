"""在远程 Docker Compose 部署中安全切换 Qwen 配置。

密钥只从当前进程环境变量读取，通过 Paramiko 的 SFTP 写入远程 `.env`，
不会写入本地文件、脚本、Git 或标准输出。
"""
from __future__ import annotations

import os
import shlex
import sys

import paramiko


HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
SSH_PASS = os.environ.get("SSH_PASS", "")
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
REMOTE_DIR = "/home/deploy/ai-interview/ai-interview-backend"
REMOTE_ENV = f"{REMOTE_DIR}/.env"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-plus")


def require_inputs() -> None:
    missing = [name for name, value in (("SSH_PASS", SSH_PASS), ("QWEN_API_KEY", QWEN_API_KEY)) if not value]
    if missing:
        raise SystemExit(f"缺少进程环境变量: {', '.join(missing)}")


def run(ssh: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = ssh.exec_command(command, timeout=120, get_pty=False)
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"远程命令失败({code}): {error[-1000:]}")
    return output


def main() -> None:
    require_inputs()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=SSH_PASS, timeout=20)
    try:
        env_dump = run(
            ssh,
            "docker inspect ai-interview-app --format '{{range .Config.Env}}{{println .}}{{end}}'",
        )
        image = run(ssh, "docker inspect ai-interview-app --format '{{.Config.Image}}'").strip()
        values: dict[str, str] = {}
        for line in env_dump.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value
        values.update(
            {
                "BACKEND_IMAGE": image,
                "AI_API_KEY": QWEN_API_KEY,
                "AI_BASE_URL": QWEN_BASE_URL,
                "AI_MODEL": QWEN_MODEL,
            }
        )
        content = "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"
        sftp = ssh.open_sftp()
        try:
            with sftp.file(REMOTE_ENV, "w") as remote_file:
                remote_file.write(content)
            sftp.chmod(REMOTE_ENV, 0o600)
        finally:
            sftp.close()

        compose = f"cd {shlex.quote(REMOTE_DIR)} && docker compose up -d --force-recreate app celery-worker celery-beat"
        run(ssh, compose)
        status = run(ssh, "docker ps --format '{{.Names}}|{{.Status}}' | grep '^ai-interview-'" )
        print("Qwen 配置已写入并完成容器重建")
        print(f"AI_MODEL={QWEN_MODEL}")
        print(f"AI_BASE_URL={QWEN_BASE_URL}")
        print(status.rstrip())
    finally:
        ssh.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
