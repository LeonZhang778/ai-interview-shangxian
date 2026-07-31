"""
SSH 端点可达性验证: 确认 P1-AI智能标签的新路由已注册。
无 token 请求应返回 401(未授权), 而非 404(路由不存在)。
"""
import os, sys, paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 未设置"); sys.exit(2)

CHECKS = [
    ("health (期望 200)",
     "curl -sL -o /dev/null -w '%{http_code}' http://localhost/api/v1/config/health; echo"),

    ("GET suggest-tags (POST路由,GET期望405=路由存在)",
     "curl -sL -o /dev/null -w '%{http_code}' http://localhost/api/v1/learning-notes/1/suggest-tags; echo"),

    ("GET apply-tags (POST路由,GET期望405=路由存在)",
     "curl -sL -o /dev/null -w '%{http_code}' http://localhost/api/v1/learning-notes/1/apply-tags; echo"),

    ("GET summary 回归 (POST路由,GET期望405=路由存在)",
     "curl -sL -o /dev/null -w '%{http_code}' http://localhost/api/v1/learning-notes/1/summary; echo"),

    ("GET 不存在路由 (期望404, 对照组)",
     "curl -sL -o /dev/null -w '%{http_code}' http://localhost/api/v1/learning-notes/1/nonexistent-route; echo"),

    ("POST suggest-tags 经 https 跟随重定向 (期望401)",
     "curl -skL -o /dev/null -w '%{http_code}' -X POST https://localhost/api/v1/learning-notes/1/suggest-tags -H 'Content-Type: application/json' -d '{}'; echo"),

    ("POST apply-tags 经 https 跟随重定向 (期望401)",
     "curl -skL -o /dev/null -w '%{http_code}' -X POST https://localhost/api/v1/learning-notes/1/apply-tags -H 'Content-Type: application/json' -d '{\"tags\":[\"Python\"]}'; echo"),

    ("app 日志尾部确认无 import 错误",
     "docker logs ai-interview-app --tail 30 2>&1 | grep -iE 'error|traceback|import|suggest|apply' | head -10 || echo NO_ERRORS_IN_LOG"),
]


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=20)
    print("SSH 连接成功\n")

    for label, cmd in CHECKS:
        print(f"{'='*60}\n>>> {label}\n{'='*60}")
        _, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if out.strip(): print(out.rstrip())
        if err.strip(): print(f"[stderr] {err.rstrip()}")
        print()

    ssh.close()


if __name__ == "__main__":
    main()
