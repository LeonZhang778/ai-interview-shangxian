import os

import paramiko

# 服务器凭据一律从环境变量读取，禁止写回代码。
# 历史上此文件硬编码了 root 口令并被提交进仓库，属于凭据泄露，已移除。
SSH_HOST = os.environ.get("DEPLOY_SSH_HOST", "8.166.120.119")
SSH_USER = os.environ.get("DEPLOY_SSH_USER", "root")
SSH_PASS = os.environ.get("DEPLOY_SSH_PASS")
if not SSH_PASS:
    raise SystemExit(
        "缺少环境变量 DEPLOY_SSH_PASS（服务器 SSH 口令）。"
        "请先 export DEPLOY_SSH_PASS=... 再运行，不要把它写回代码。"
    )

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

# Copy SQL file to postgres container and run it
cmds = [
    'docker cp /home/deploy/ai-interview/ai-interview-backend/migrations/create_experiences_tables.sql ai-interview-postgres:/tmp/create_exp.sql',
    'docker exec ai-interview-postgres psql -U postgres -d postgres -f /tmp/create_exp.sql',
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out)
    if err:
        print(err)

# Verify
stdin, stdout, stderr = ssh.exec_command('docker exec ai-interview-postgres psql -U postgres -d postgres -c "\\dt"')
print(stdout.read().decode())

ssh.close()
