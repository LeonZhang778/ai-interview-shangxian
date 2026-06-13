# AI-Interview 服务器部署流程

服务器: `8.166.120.119` | 系统: Ubuntu 22.04

---

## 第一步: 本地推送到 GitHub

### 1.1 在 GitHub 上创建仓库

1. 打开 https://github.com/new
2. Repository name: `ai-interview`
3. 选 **Private** (项目包含 API Key 和邮箱密码)
4. 不要勾选 README / .gitignore
5. 点 Create repository

### 1.2 本地初始化并推送

打开 PowerShell, 进入项目根目录:

```powershell
cd D:\ai-interview

# 初始化 Git
git init
git branch -M main

# 添加远程仓库 (替换成你的 GitHub 用户名)
git remote add origin https://github.com/你的用户名/ai-interview.git
```

### 1.3 确认 .gitignore 生效

```powershell
# 查看哪些文件会被提交 (应该不包含 node_modules, .venv, logs 等)
git status
```

确认以下文件**不会**出现:
- `ai-interview/ai-interview-frontend/node_modules/`
- `ai-interview/.venv/`
- `ai-interview/ai-interview-backend/logs/`
- `ai-interview/ai-interview-script-md-pdf/`
- `ai-interview/ai-interview学习记录/`
- `start.ps1`, `stop.ps1`, `启动.bat`, `停止.bat`
- `.vscode/`

### 1.4 提交并推送

```powershell
git add .
git commit -m "init: AI-Interview 项目完整代码"
git push -u origin main --force
```

### 1.5 项目结构 (推送到 GitHub 后的样子)

```
ai-interview/                    ← 仓库根目录
├── .gitignore
├── CLAUDE.md
├── README.md
└── ai-interview/
    ├── ai-interview-backend/    ← FastAPI 后端
    │   ├── app/
    │   ├── nginx/
    │   ├── scripts/
    │   ├── migrations/
    │   ├── Dockerfile
    │   ├── Dockerfile.dev
    │   ├── docker-compose.yml
    │   ├── docker-compose.dev.yml
    │   ├── docker-compose.prod.yml
    │   ├── requirements.txt
    │   ├── main.py
    │   ├── alembic.ini
    │   ├── .env                 ← 包含 API Key 和邮箱配置
    │   └── .env.production
    ├── ai-interview-frontend/   ← Vue 用户端前端
    │   ├── src/
    │   ├── package.json
    │   └── vite.config.js
    └── ai-interview-admin/      ← Vue 管理后台
        ├── src/
        ├── package.json
        └── vite.config.js
```

---

## 第二步: 服务器初始化

SSH 登录服务器:

```bash
ssh root@8.166.120.119
```

### 2.1 系统更新

```bash
apt update && apt upgrade -y
apt install -y curl wget git vim
```

### 2.2 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker
```

### 2.3 安装 Docker Compose

```bash
apt install -y docker-compose-plugin
```

### 2.4 配置安全组 (云控制台)

在阿里云/腾讯云控制台的安全组中放行:

| 端口 | 协议 | 用途 |
|------|------|------|
| 22 | TCP | SSH |
| 80 | TCP | HTTP |
| 443 | TCP | HTTPS |

> 不要放行 5432 和 6379!

### 2.5 防火墙

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## 第三步: 从 GitHub 拉取代码

```bash
# 创建部署目录
mkdir -p /home/deploy
cd /home/deploy

# 克隆仓库 (替换成你的 GitHub 地址)
git clone https://github.com/你的用户名/ai-interview.git

# 查看目录结构
ls ai-interview/
# 应该看到: CLAUDE.md  README.md  ai-interview/
```

---

## 第四步: 整理文件到正确位置

GitHub 仓库多了一层 `ai-interview/` 目录, 需要把项目文件提到部署根目录:

```bash
cd /home/deploy

# 把项目内容移到 deploy 根目录
mv ai-interview/ai-interview/* ai-interview/
mv ai-interview/ai-interview/.* ai-interview/ 2>/dev/null
rmdir ai-interview/ai-interview 2>/dev/null

# 验证目录结构
ls ai-interview/
# 应该看到: ai-interview-backend  ai-interview-frontend  ai-interview-admin  ...
```

现在的服务器目录结构:

```
/home/deploy/ai-interview/
├── ai-interview-backend/    ← 后端
├── ai-interview-frontend/   ← 前端 (源码, 需要构建)
├── ai-interview-admin/      ← 后台 (源码, 需要构建)
├── CLAUDE.md
└── README.md
```

---

## 第五步: 构建前端

服务器上需要安装 Node.js 来构建前端:

```bash
# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 验证
node -v
npm -v
```

### 5.1 构建用户端前端

```bash
cd /home/deploy/ai-interview/ai-interview-frontend
npm install
npm run build
# 生成 dist/ 目录
```

### 5.2 构建管理后台

```bash
cd /home/deploy/ai-interview/ai-interview-admin
npm install
npm run build
# 生成 dist/ 目录
```

### 5.3 验证

```bash
ls /home/deploy/ai-interview/ai-interview-frontend/dist/
ls /home/deploy/ai-interview/ai-interview-admin/dist/
# 两个目录都应该有 index.html
```

---

## 第六步: 配置生产环境 .env

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# .env 已经从 GitHub 拉下来了, 包含 API Key 和邮箱配置
# 只需要修改生产环境特有的配置

# 查看当前 .env
cat .env
```

### 6.1 需要修改的配置

用 `vim .env` 编辑以下内容:

```bash
vim .env
```

修改以下行:

```env
# 开发环境 → 生产环境
ENV=production

# localhost → Docker 内部服务名
POSTGRES_HOST=postgres
REDIS_HOST=redis

# 设置 Redis 密码 (生产环境必须)
REDIS_PASSWORD=R3d!s_A1_2026_Sec

# 改用强密码 (替换 123456)
POSTGRES_PASSWORD=Xk9$mP2vL7qR4wN8

# 改用自定义数据库名
POSTGRES_DB=ai_interview
POSTGRES_USER=ai_user

# JWT 密钥替换为强密钥
SECRET_KEY=a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0

# 前端地址 (暂时用 IP, 绑域名后改)
FRONTEND_URL=http://8.166.120.119

# API 端口 (与 Dockerfile.dev 一致)
API_PORT=8001
```

### 6.2 不需要修改的配置

以下保持原样:

```env
# QQ 邮箱 (确认授权码有效即可)
MAIL_HOST=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=1448203623@qq.com
MAIL_PASSWORD=qxxbeqhanjsbjcga

# 智谱 GLM (确认有额度即可)
AI_API_KEY=70041ddde9824461bfb02fac3f469fc3.pDZCoxOgkovIx1vT
AI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
AI_MODEL=glm-4.7-flash
```

### 6.3 凭据速查表 (保存到本地)

| 项目 | 值 |
|------|-----|
| PostgreSQL 用户名 | `ai_user` |
| PostgreSQL 密码 | `Xk9$mP2vL7qR4wN8` |
| PostgreSQL 数据库 | `ai_interview` |
| Redis 密码 | `R3d!s_A1_2026_Sec` |
| JWT SECRET_KEY | `a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0` |

---

## 第七步: 启动所有服务

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# 一键启动 6 个容器
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

首次构建约 3-5 分钟, 等待完成后检查:

```bash
# 查看容器状态 (应该有 6 个)
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

预期输出:

```
NAME                    STATUS
ai-interview-app        Up (healthy)
ai-interview-celery-worker  Up
ai-interview-celery-beat    Up
ai-interview-postgres   Up (healthy)
ai-interview-redis      Up (healthy)
ai-interview-nginx      Up
```

```bash
# 查看后端日志确认无报错
docker compose logs -f app --tail 30
```

成功日志:

```
INFO:     Application starting up
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## 第八步: 数据库迁移 & 创建管理员

```bash
# 数据库迁移
docker exec -it ai-interview-app alembic upgrade head

# 创建管理员 (按提示输入邮箱和密码)
docker exec -it ai-interview-app python scripts/create_first_admin.py
```

---

## 第九步: 验证

### 健康检查

```bash
curl http://localhost:8001/api/v1/config/health
# 返回 {"code":200,"message":"Success","data":{"status":"healthy"}}
```

### 浏览器访问

| 页面 | 地址 |
|------|------|
| 用户端 | `http://8.166.120.119` |
| 管理后台 | `http://8.166.120.119/admin` |
| 健康检查 | `http://8.166.120.119/health` |

---

## 第十步: 后续更新流程

以后修改代码后, 按以下步骤更新:

```bash
# ---- 本地 PowerShell ----
cd D:\ai-interview
git add .
git commit -m "update: 描述"
git push

# ---- 服务器 SSH ----
cd /home/deploy/ai-interview
git pull

# 如果改了后端代码
cd ai-interview-backend
docker compose restart app celery-worker

# 如果改了前端代码
cd ../ai-interview-frontend && npm run build
cd ../ai-interview-admin && npm run build
docker compose restart nginx

# 如果改了 docker-compose 或 Dockerfile
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 第十一步: 域名 & HTTPS (有域名后)

### 11.1 购买域名 + ICP 备案

国内服务器必须备案, 阿里云/腾讯云免费备案, 约 1-2 周。

### 11.2 域名解析

添加 A 记录指向 `8.166.120.119`。

### 11.3 申请 SSL 证书

```bash
apt install -y certbot

# 停止 Nginx 释放 80 端口
cd /home/deploy/ai-interview/ai-interview-backend
docker compose stop nginx

# 申请证书
certbot certonly --standalone -d 你的域名 -d www.你的域名

# 复制证书到项目
mkdir -p ssl
cp /etc/letsencrypt/live/你的域名/fullchain.pem ssl/
cp /etc/letsencrypt/live/你的域名/privkey.pem ssl/
```

### 11.4 修改配置启用 HTTPS

编辑 `nginx/default.conf`, 把 `server { listen 80; ... }` 改为:

```nginx
server {
    listen 443 ssl http2;
    server_name 你的域名 www.你的域名;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # location 配置和之前一样, 不变
    # ...
}

server {
    listen 80;
    server_name 你的域名 www.你的域名;
    return 301 https://$host$request_uri;
}
```

编辑 `docker-compose.yml`, 取消 nginx volumes 中 ssl 的注释:

```yaml
- ./ssl:/etc/nginx/ssl:ro
```

编辑 `.env`:

```env
FRONTEND_URL=https://你的域名
```

重启:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 常用运维命令

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# 查看容器状态
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 查看后端日志
docker compose logs -f app --tail 100

# 查看 Celery 日志
docker compose logs -f celery-worker --tail 100

# 查看 Nginx 日志
docker compose logs -f nginx --tail 100

# 重启后端
docker compose restart app

# 重启所有服务
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart

# 进入后端容器
docker exec -it ai-interview-app bash

# 进入数据库
docker exec -it ai-interview-postgres psql -U ai_user -d ai_interview

# 健康检查
curl http://localhost:8001/api/v1/config/health

# 查看磁盘
df -h

# 清理 Docker 无用镜像
docker system prune -f
```

---

## 架构总览

```
用户浏览器
    ↓
  Nginx (Docker 容器, port 80/443)
    ├── /         → 用户端前端 (dist, volume 映射)
    ├── /admin    → 管理后台 (dist, volume 映射)
    ├── /api/     → FastAPI 后端 (Docker 内部, app:8001)
    └── /uploads/ → 上传文件

FastAPI 后端 (app:8001)
    ├── PostgreSQL (postgres:5432)
    ├── Redis (redis:6379)
    ├── Celery Worker (异步邮件)
    └── 智谱 GLM API (外部)
```

6 个容器全部在 Docker 内部通信, 只有 Nginx 暴露 80/443 给外网。

---

## 常见问题

### Q: git push 时提示 .env 被忽略

检查 `ai-interview-backend/.gitignore` 中 `.env` 是否被注释掉:

```bash
# 应该是这样 (被注释):
# .env
```

### Q: 502 Bad Gateway

```bash
docker compose ps           # 检查 app 是否运行
docker compose logs app     # 看报错
```

### Q: 前端 404

```bash
# 检查 dist 是否存在
ls /home/deploy/ai-interview/ai-interview-frontend/dist/
ls /home/deploy/ai-interview/ai-interview-admin/dist/
```

### Q: 邮件发送失败

QQ 邮箱授权码过期, 修改 `.env` 中 `MAIL_PASSWORD`:

```bash
docker compose restart app celery-worker
```

### Q: 磁盘满了

```bash
docker system prune -f
truncate -s 0 /home/deploy/ai-interview/ai-interview-backend/logs/*.log
```

---

## 部署清单

- [ ] GitHub 创建 Private 仓库
- [ ] 本地 `git push` 到 GitHub
- [ ] 服务器安装 Docker
- [ ] 服务器 `git clone` 拉取代码
- [ ] 整理目录结构 (mv 去掉多余层级)
- [ ] 安装 Node.js + 构建前端 (npm run build)
- [ ] 修改 `.env` 生产环境配置
- [ ] `docker compose up -d --build`
- [ ] 数据库迁移 (alembic upgrade head)
- [ ] 创建管理员 (create_first_admin.py)
- [ ] 浏览器访问验证
- [ ] (可选) 域名 + HTTPS
