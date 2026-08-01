"""
登录 500 排障: SSH 到服务器抓取后端日志、迁移状态、健康检查。
凭据从环境变量 SSH_HOST/SSH_USER/SSH_PASS 读取,不打印密码。
用法:
    $env:SSH_PASS='你的密码'; python scripts/codepus-agent/ssh_login_log.py
"""
import os
import sys
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 未设置。请先 $env:SSH_PASS='密码' 再运行本脚本。")
    sys.exit(2)

# 排障命令清单(不输出凭据)
CHECKS = [
    ("1. 健康检查 nginx->app",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/v1/config/health 2>&1; echo"),

    ("2. 登录接口直接探测(app 容器内, 用空 body 看 500 还是 422)",
     "docker exec ai-interview-app curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8006/api/v1/auth/login -H 'Content-Type: application/json' -d '{}' 2>&1; echo"),

    ("3. 后端容器最近 200 行日志(重点看 login / 500 / Error / Traceback)",
     "docker logs ai-interview-app --tail 200 2>&1 | grep -iE 'login|500|error|traceback|exception|import|nameerror|modulenotfound' | tail -60"),

    ("4. 后端容器全部最近日志尾部(上下文)",
     "docker logs ai-interview-app --tail 50 2>&1"),

    ("5. alembic 当前版本(应为 h1a2b3c4d5e6, 否则迁移未执行)",
     "docker exec ai-interview-app alembic current 2>&1"),

    ("6. 容器状态",
     "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' | grep -E 'ai-interview|NAMES' 2>&1"),

    ("7. learning_notes 表是否有 summary/key_points 列(迁移是否落地)",
     "docker exec ai-interview-postgres psql -U demo -d ai_interview -t -c \"SELECT column_name FROM information_schema.columns WHERE table_name='learning_notes' AND column_name IN ('summary','key_points');\" 2>&1"),
]


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=20)
        print("SSH 连接成功\n")
    except Exception as e:
        print(f"SSH 连接失败: {e}")
        sys.exit(3)

    for label, cmd in CHECKS:
        print(f"{'='*70}\n>>> {label}\n{'='*70}")
        try:
            _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            if out.strip():
                print(out.rstrip())
            if err.strip():
                print(f"[stderr] {err.rstrip()}")
            print(f"[exit={rc}]\n")
        except Exception as e:
            print(f"[执行异常] {e}\n")

    ssh.close()
    print("SSH 已关闭。")


if __name__ == "__main__":
    main()
