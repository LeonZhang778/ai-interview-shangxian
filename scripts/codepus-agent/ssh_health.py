"""
SSH 部署后健康验证 (CodePus autonomous)。
通过 nginx 80 端口(宿主机外部可达)验证服务可用性,并检查迁移是否生效。
从环境变量 SSH_HOST/SSH_USER/SSH_PASS 读取凭据。
"""
import os
import sys
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 未设置"); sys.exit(2)

CHECKS = [
    ("健康检查 (nginx 80 -> app)",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/v1/config/health 2>&1; echo"),

    ("健康检查 (直接 app 容器内)",
     "docker exec ai-interview-app curl -s -o /dev/null -w '%{http_code}' http://localhost:8006/api/v1/config/health 2>&1; echo"),

    ("健康响应体",
     "curl -s http://localhost/api/v1/config/health 2>&1; echo"),

    ("page_view 表结构(迁移是否生效-应有 ip/country/province 列)",
     "docker exec ai-interview-postgres psql -U demo -d ai_interview -c '\\d page_views' 2>&1 | grep -E 'ip|country|province' || echo 'GEO_COLUMNS_MISSING'"),

    ("page_view 最近记录数",
     "docker exec ai-interview-postgres psql -U demo -d ai_interview -c 'SELECT count(*) FROM page_views;' 2>&1 | sed -n '3,4p'"),

    ("新端点 /notes/suggest-tags (无token应401非404)",
     "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost/api/v1/notes/suggest-tags -H 'Content-Type: application/json' -d '{}' 2>&1; echo"),

    ("新端点 /notes/apply-tags (无token应401非404)",
     "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost/api/v1/notes/apply-tags -H 'Content-Type: application/json' -d '{}' 2>&1; echo"),

    ("前端首页可达性",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost/ 2>&1; echo"),

    ("管理后台可达性",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost/admin/ 2>&1; echo"),

    ("后端日志尾部(确认无报错)",
     "docker logs ai-interview-app --tail 15 2>&1"),

    ("迁移版本号(应为 g0b1c2d3e4f5)",
     "docker exec ai-interview-app alembic current 2>&1"),
]


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=20)
    print("SSH 连接成功\n")

    for label, cmd in CHECKS:
        print(f"{'='*60}\n>>> {label}\n{'='*60}")
        _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        if out.strip(): print(out.rstrip())
        if err.strip(): print(f"[stderr] {err.rstrip()}")
        print(f"[exit={rc}]\n")

    ssh.close()


if __name__ == "__main__":
    main()
