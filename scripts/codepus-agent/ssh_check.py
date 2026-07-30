#!/usr/bin/env python3
"""通过 paramiko 连接服务器执行只读诊断命令。

用法:
  python scripts/codepus-agent/ssh_check.py "<远程命令>"

环境变量:
  SSH_HOST / SSH_USER / SSH_PASS  (默认 deploy@8.166.120.119 / 5408854088Ab@)
"""
import os
import sys
import paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "deploy")
PASS = os.environ.get("SSH_PASS", "5408854088Ab@")

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
