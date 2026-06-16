"""部署面经广场功能"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import paramiko

SERVER = "8.166.120.119"
USER = "root"
PASSWORD = "5408854088Ab@"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASSWORD)

def run(cmd):
    print(f">>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out.strip())
    if err.strip():
        print(f"STDERR: {err.strip()}")
    return out, err

# 1. 创建数据库表
print("=" * 60)
print("1. 创建数据库表")
print("=" * 60)

sql = """
CREATE TABLE IF NOT EXISTS experiences (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    company         VARCHAR(50) NOT NULL,
    position        VARCHAR(50) NOT NULL,
    level           VARCHAR(20),
    round           VARCHAR(20),
    content         TEXT NOT NULL,
    summary         VARCHAR(500),
    view_count      INTEGER DEFAULT 0,
    like_count      INTEGER DEFAULT 0,
    collect_count   INTEGER DEFAULT 0,
    author_id       INTEGER REFERENCES users(id),
    is_anonymous    BOOLEAN DEFAULT true,
    status          VARCHAR(20) DEFAULT 'published',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS experience_tags (
    experience_id   INTEGER REFERENCES experiences(id) ON DELETE CASCADE,
    tag             VARCHAR(30),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (experience_id, tag)
);

CREATE TABLE IF NOT EXISTS user_collections (
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    experience_id   INTEGER REFERENCES experiences(id) ON DELETE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, experience_id)
);

CREATE INDEX IF NOT EXISTS idx_experiences_company ON experiences(company);
CREATE INDEX IF NOT EXISTS idx_experiences_position ON experiences(position);
CREATE INDEX IF NOT EXISTS idx_experiences_status ON experiences(status);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at DESC);
"""

run(f"cat > /tmp/create_experiences.sql << 'SQLEOF'\n{sql}\nSQLEOF")
run("sudo docker exec -i ai-interview-postgres psql -U ai_user -d ai_interview < /tmp/create_experiences.sql")

# 2. 复制后端文件
print("=" * 60)
print("2. 复制后端文件")
print("=" * 60)

sftp = ssh.open_sftp()

backend_files = [
    ("ai-interview-backend/app/models/experience.py", "/home/deploy/ai-interview/ai-interview-backend/app/models/experience.py"),
    ("ai-interview-backend/app/models/__init__.py", "/home/deploy/ai-interview/ai-interview-backend/app/models/__init__.py"),
    ("ai-interview-backend/app/schemas/client/experience.py", "/home/deploy/ai-interview/ai-interview-backend/app/schemas/client/experience.py"),
    ("ai-interview-backend/app/services/client/experience_service.py", "/home/deploy/ai-interview/ai-interview-backend/app/services/client/experience_service.py"),
    ("ai-interview-backend/app/api/client/v1/experience.py", "/home/deploy/ai-interview/ai-interview-backend/app/api/client/v1/experience.py"),
    ("ai-interview-backend/app/route/router_registry.py", "/home/deploy/ai-interview/ai-interview-backend/app/route/router_registry.py"),
]

for local, remote in backend_files:
    print(f"  Upload: {local}")
    sftp.put(local, remote)

# 3. 复制前端源文件
print("=" * 60)
print("3. 复制前端源文件")
print("=" * 60)

frontend_files = [
    ("ai-interview-frontend/src/api/experience.js", "/home/deploy/ai-interview/ai-interview-frontend/src/api/experience.js"),
    ("ai-interview-frontend/src/views/Experiences.vue", "/home/deploy/ai-interview/ai-interview-frontend/src/views/Experiences.vue"),
    ("ai-interview-frontend/src/views/ExperienceDetail.vue", "/home/deploy/ai-interview/ai-interview-frontend/src/views/ExperienceDetail.vue"),
    ("ai-interview-frontend/src/router/index.js", "/home/deploy/ai-interview/ai-interview-frontend/src/router/index.js"),
    ("ai-interview-frontend/src/App.vue", "/home/deploy/ai-interview/ai-interview-frontend/src/App.vue"),
]

for local, remote in frontend_files:
    print(f"  Upload: {local}")
    sftp.put(local, remote)

# 4. 创建 public 目录并上传静态文件
print("=" * 60)
print("4. 上传静态文件到 public/")
print("=" * 60)
run("mkdir -p /home/deploy/ai-interview/ai-interview-frontend/public")
sftp.put("ai-interview-frontend/public/sitemap.xml", "/home/deploy/ai-interview/ai-interview-frontend/public/sitemap.xml")
sftp.put("ai-interview-frontend/public/robots.txt", "/home/deploy/ai-interview/ai-interview-frontend/public/robots.txt")
print("  Upload: sitemap.xml, robots.txt")

sftp.close()

# 5. 重启后端容器
print("=" * 60)
print("5. 重启后端容器")
print("=" * 60)
run("sudo docker restart ai-interview-app")

# 6. 构建前端
print("=" * 60)
print("6. 构建前端")
print("=" * 60)
run("cd /home/deploy/ai-interview/ai-interview-frontend && npm run build")

# 7. 重启 nginx
print("=" * 60)
print("7. 重启 nginx")
print("=" * 60)
run("sudo docker restart ai-interview-nginx")

# 8. 验证
print("=" * 60)
print("8. 验证")
print("=" * 60)
run("sudo docker exec ai-interview-postgres psql -U ai_user -d ai_interview -c '\\dt experiences%'")
run("curl -s http://localhost:8006/api/v1/experiences | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8006/api/v1/experiences")

print("=" * 60)
print("部署完成!")
print("=" * 60)

ssh.close()
