"""通过 SSH 验证远程 Qwen 配置和最小 API 请求，不输出密钥或响应正文。"""
from __future__ import annotations

import os
import paramiko


HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASSWORD = os.environ.get("SSH_PASS", "")

REMOTE_SCRIPT = r'''
import json
import os
import urllib.request

base_url = os.environ["AI_BASE_URL"]
model = os.environ["AI_MODEL"]
api_key = os.environ["AI_API_KEY"]
payload = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "只回复：连接正常"}],
    "max_tokens": 16,
}).encode()
request = urllib.request.Request(
    base_url + "/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    },
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print("QWEN_HTTP_STATUS=" + str(response.status))
        print("QWEN_API_CALL=success")
except Exception as exc:
    print("QWEN_API_CALL=failed")
    print("QWEN_ERROR_TYPE=" + type(exc).__name__)
    raise
'''


if not PASSWORD:
    raise SystemExit("缺少 SSH_PASS")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
try:
    command = "docker exec -i ai-interview-app python -"
    stdin, stdout, stderr = ssh.exec_command(command, timeout=60, get_pty=False)
    stdin.write(REMOTE_SCRIPT)
    stdin.channel.shutdown_write()
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if output:
        print(output.rstrip())
    if code:
        print("远程验证失败，未输出响应正文或密钥。")
        if error:
            print("错误类型=" + error.splitlines()[-1][:200])
        raise SystemExit(code)
finally:
    ssh.close()
