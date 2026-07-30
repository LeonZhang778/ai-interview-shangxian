#!/usr/bin/env python3
"""SSH diagnostics: check backend status on remote server."""
import paramiko

HOST = "8.166.120.119"
USER = "root"
PASS = "5408854088Ab@"

CMDS = r"""
echo '=== 1. 系统概览 ==='
echo '--- 内存 ---'
free -h | head -2
echo '--- 磁盘 ---'
df -h / | tail -1
echo '--- Uptime ---'
uptime
echo '--- Docker ---'
docker --version 2>&1
echo ''
echo '=== 2. 所有容器状态 ==='
docker ps -a --filter name=ai-interview --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo ''
echo '=== 3. 健康检查 (直接本机) ==='
echo '--- curl localhost:8006 ---'
curl -s -o /dev/null -w 'HTTP %{http_code} | %{time_total}s' --max-time 10 http://localhost:8006/api/v1/config/health 2>&1 || echo 'FAIL'
echo ''
echo '--- curl localhost:80 (nginx) ---'
curl -s -o /dev/null -w 'HTTP %{http_code} | %{time_total}s' --max-time 10 http://localhost:80/api/v1/config/health 2>&1 || echo 'FAIL'
echo ''
echo '=== 4. 应用日志 (最近30行) ==='
docker logs ai-interview-app --tail 30 2>&1 | head -30
echo ''
echo '=== 5. Nginx 日志 (最近20行) ==='
docker logs ai-interview-nginx --tail 20 2>&1 | head -20
echo ''
echo '=== 6. 容器资源占用 ==='
docker stats --no-stream --filter name=ai-interview --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'
echo ''
echo '=== 7. 后端进程 ==='
docker exec ai-interview-app ps aux 2>&1 | head -10 || echo 'FAIL'
echo ''
echo '=== 8. 数据库连接检查 ==='
docker exec ai-interview-app python -c "import urllib.request; print('Health:', urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=5).status)" 2>&1 || echo 'FAIL'
echo ''
echo '=== 9. docker-compose 部署目录 ==='
ls -la /home/deploy/ai-interview/ai-interview-backend/ 2>&1 | head -5
echo ''
echo '=== 10. .env 文件 ==='
ls -la /home/deploy/ai-interview/ai-interview-backend/.env 2>&1 || echo 'NO .ENV'
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15, look_for_keys=False, allow_agent=False)

stdin, stdout, stderr = client.exec_command(CMDS, timeout=60, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
print("EXIT:", code)
print(out)
if err.strip():
    print("=== STDERR ===")
    print(err)
client.close()