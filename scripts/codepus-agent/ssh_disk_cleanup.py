"""
服务器磁盘清理 + 服务恢复。
1. 清理 docker 悬空镜像/构建缓存(释放 ~27GB)
2. 清理容器旧日志
3. 重启 postgres, 等待恢复完成
4. 重启 app
5. 执行 alembic upgrade head
6. 验证健康检查 + 登录接口
凭据从环境变量读取,不打印密码。
"""
import os, sys, time, paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 未设置"); sys.exit(2)

STEPS = [
    ("STEP 1: 清理前磁盘状态",
     "df -h / 2>&1 | tail -2; echo; docker system df 2>&1"),

    ("STEP 2: 清理 docker 悬空镜像(dangling)",
     "docker image prune -f 2>&1"),

    ("STEP 3: 清理 docker 所有未使用镜像(保留运行中容器用到的)",
     "docker image prune -a -f --filter 'until=24h' 2>&1"),

    ("STEP 4: 清理 docker 构建缓存",
     "docker builder prune -f 2>&1"),

    ("STEP 5: 清理后磁盘状态",
     "df -h / 2>&1 | tail -2; echo; docker system df 2>&1"),

    ("STEP 6: 截断容器旧日志(保留最近)",
     "for c in ai-interview-app ai-interview-postgres ai-interview-celery-worker ai-interview-celery-beat ai-interview-redis ai-interview-nginx; do p=$(docker inspect --format='{{.LogPath}}' $c 2>/dev/null); if [ -n \"$p\" ]; then truncate -s 0 \"$p\" 2>/dev/null && echo \"truncated $c\"; fi; done; echo done"),

    ("STEP 7: 重启 postgres 让它完成恢复",
     "docker restart ai-interview-postgres 2>&1"),

    ("STEP 8: 等待 20 秒让 postgres 恢复",
     "sleep 20; echo 'slept 20s'"),

    ("STEP 9: 检查 postgres 是否接受连接",
     "docker exec ai-interview-postgres pg_isready -U demo -d ai_interview 2>&1"),

    ("STEP 10: 重启 app 容器",
     "docker restart ai-interview-app 2>&1"),

    ("STEP 11: 等待 10 秒让 app 启动",
     "sleep 10; echo 'slept 10s'"),

    ("STEP 12: 健康检查",
     "curl -s -o /dev/null -w '%{http_code}' http://localhost/api/v1/config/health 2>&1; echo"),

    ("STEP 13: alembic upgrade head 执行新迁移",
     "docker exec ai-interview-app alembic upgrade head 2>&1"),

    ("STEP 14: 确认迁移版本",
     "docker exec ai-interview-app alembic current 2>&1"),

    ("STEP 15: 登录接口探测(空 body 应 422 不是 500)",
     "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost/api/v1/auth/login -H 'Content-Type: application/json' -d '{}' 2>&1; echo"),

    ("STEP 16: 容器状态总览",
     "docker ps --format 'table {{.Names}}\\t{{.Status}}' 2>&1"),
]


def main():
    print(f"Connecting to {USER}@{HOST} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=20)
        print("SSH 连接成功\n")
    except Exception as e:
        print(f"SSH 连接失败: {e}"); sys.exit(3)

    for label, cmd in STEPS:
        print(f"{'='*70}\n>>> {label}\n{'='*70}")
        try:
            _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            rc = stdout.channel.recv_exit_status()
            if out.strip(): print(out.rstrip())
            if err.strip(): print(f"[stderr] {err.rstrip()}")
            print(f"[exit={rc}]\n")
        except Exception as e:
            print(f"[执行异常] {e}\n")
    ssh.close()
    print("SSH 已关闭。")


if __name__ == "__main__":
    main()
