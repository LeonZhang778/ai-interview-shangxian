"""
服务器磁盘诊断: 定位磁盘空间被什么吃满, 为清理做准备。
凭据从环境变量 SSH_HOST/SSH_USER/SSH_PASS 读取,不打印密码。
"""
import os, sys, paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS:
    print("ERROR: SSH_PASS 未设置"); sys.exit(2)

CHECKS = [
    ("1. 整体磁盘占用",
     "df -h 2>&1"),

    ("2. /var 总体(常见日志/docker 挂载点)",
     "du -sh /var/* 2>/dev/null | sort -rh | head -20"),

    ("3. docker 占用明细",
     "docker system df 2>&1"),

    ("4. docker 容器日志大小 Top10",
     "for c in $(docker ps -a --format '{{.Names}}'); do sz=$(docker inspect --format='{{.LogPath}}' $c 2>/dev/null | xargs du -sh 2>/dev/null | cut -f1); echo \"$sz  $c\"; done | sort -rh | head -10"),

    ("5. /var/lib/docker 子目录",
     "du -sh /var/lib/docker/* 2>/dev/null | sort -rh | head -10"),

    ("6. postgres 数据目录(WAL 是否堆积)",
     "du -sh /var/lib/docker/volumes/*postgres*/_data/* 2>/dev/null | sort -rh | head -15"),

    ("7. 系统大文件 Top15",
     "find / -xdev -type f -size +100M 2>/dev/null | xargs du -h 2>/dev/null | sort -rh | head -15"),

    ("8. /tmp 与日志文件",
     "du -sh /tmp /var/log /var/log/* 2>/dev/null | sort -rh | head -15"),

    ("9. postgres 容器内 WAL 与日志",
     "docker exec ai-interview-postgres sh -c 'du -sh /var/lib/postgresql/data/pg_wal 2>/dev/null; ls -lhS /var/lib/postgresql/data/log 2>/dev/null | head -5; du -sh /var/lib/postgresql/data/log 2>/dev/null' 2>&1"),
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

    for label, cmd in CHECKS:
        print(f"{'='*70}\n>>> {label}\n{'='*70}")
        try:
            _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
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
