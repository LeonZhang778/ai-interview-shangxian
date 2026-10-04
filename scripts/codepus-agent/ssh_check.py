#!/usr/bin/env python3
"""通过 paramiko 连接服务器执行只读诊断命令。

用法:
  python scripts/codepus-agent/ssh_check.py "<远程命令>"

环境变量:
  SSH_HOST / SSH_USER / SSH_PASS   （口令不再提供默认值，必须显式设置）
"""
import os
import sys
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "deploy")
# 不再提供硬编码默认口令（历史上这里写了明文 root/deploy 口令并被提交进仓库）
PASS = os.environ.get("SSH_PASS")
if not PASS:
    print("[SSH CONFIG FAIL] 缺少环境变量 SSH_PASS，请显式设置后再运行。", file=sys.stderr)
    sys.exit(2)

cmd = sys.argv[1] if len(sys.argv) > 1 else "echo SSH_OK && hostname"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect(HOST, username=USER, password=PASS, timeout=15)
except Exception as e:
    print(f"[SSH CONNECT FAIL] {e}", file=sys.stderr)
    sys.exit(2)

stdin, stdout, stderr = client.exec_command(cmd, timeout=60, get_pty=False)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
if out:
    print(out, end="")
if err:
    print("--- STDERR ---", file=sys.stderr)
    print(err, end="", file=sys.stderr)
client.close()
sys.exit(code)
