"""
SSH 迁移诊断: 用正确的生产凭据(postgres/postgres)查 page_views 表结构,
确认迁移 g0b1c2d3e4f5 的 ip/country/province/user_agent 列真实存在。
"""
import os, sys, paramiko

HOST = os.environ.get("SSH_HOST", "8.166.120.119")
USER = os.environ.get("SSH_USER", "root")
PASS = os.environ.get("SSH_PASS", "")
if not PASS: print("ERROR: SSH_PASS 未设置"); sys.exit(2)

# 用单引号包裹的 SQL,避免 shell 引号问题
CMD = r"""bash -c '
echo "=== page_views 列名(应有 ip/country/province/user_agent) ==="
docker exec ai-interview-postgres psql -U postgres -d postgres -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='"'"'page_views'"'"' ORDER BY ordinal_position;" 2>&1

echo
echo "=== page_views 索引 ==="
docker exec ai-interview-postgres psql -U postgres -d postgres -t -c "SELECT indexname FROM pg_indexes WHERE tablename='"'"'page_views'"'"';" 2>&1

echo
echo "=== alembic_version 表 ==="
docker exec ai-interview-postgres psql -U postgres -d postgres -c "SELECT * FROM alembic_version;" 2>&1

echo
echo "=== page_views 记录数 ==="
docker exec ai-interview-postgres psql -U postgres -d postgres -c "SELECT count(*) FROM page_views;" 2>&1
'
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)
_, stdout, stderr = ssh.exec_command(CMD, timeout=60)
print(stdout.read().decode("utf-8", errors="replace"))
e = stderr.read().decode("utf-8", errors="replace")
if e.strip(): print("[stderr]", e)
ssh.close()
