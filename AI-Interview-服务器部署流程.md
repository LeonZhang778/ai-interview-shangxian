# AI-Interview 服务器部署流程

服务器: `8.166.120.119` | 域名: `zhangzhengqiang.xyz` | 系统: Ubuntu 22.04

---

## 第一步: 本地推送到 GitHub

### 1.1 仓库信息

- GitHub 仓库: `git@github.com:LeonZhang778/ai-interview-shangxian.git`
- 远程别名: `origin`
- 分支: `main`

### 1.2 本地推送

```powershell
cd C:\Users\admin\Desktop\ai-interview-shangxian

# 如果尚未关联远程仓库
git remote add origin git@github.com:LeonZhang778/ai-interview-shangxian.git

# 提交并推送
git add .
git commit -m "update: 描述本次修改"
git push -u origin main
```

### 1.3 项目结构（推送到 GitHub 后的样子）

```
ai-interview-shangxian/           ← 仓库根目录
├── .gitignore
├── CLAUDE.md
├── README.md
├── ai-interview-backend/         ← FastAPI 后端 + 6 个 Docker 容器
│   ├── app/
│   │   ├── api/                  ← 客户端 (21 路由) + 后台 (13 路由) API 注册
│   │   ├── core/                 ← 配置、安全、Celery、日志
│   │   ├── models/               ← SQLAlchemy 数据模型 (22 个模型)
│   │   ├── schemas/              ← Pydantic 请求/响应校验
│   │   ├── services/             ← 业务逻辑层 (客户端 / 后台 / 通用 / 媒体)
│   │   ├── graphs/               ← LangGraph 面试状态机
│   │   ├── schedule/jobs/        ← Celery 定时任务 (邮件/图片/媒体/示例)
│   │   ├── prompts/              ← AI 提示词
│   │   ├── common/               ← 审计、日志消费、语言、发布
│   │   ├── route/                ← 路由注册中心 (router_registry.py)
│   │   └── utils/                ← 工具函数
│   ├── nginx/                    ← Docker Nginx 配置 (default.conf, 端口 8080)
│   ├── migrations/versions/      ← Alembic 迁移 (18 个版本)
│   ├── scripts/                  ← 管理脚本 (create_first_admin, seed_settings)
│   ├── app/scripts/seed_admin.py ← 默认管理员种子脚本
│   ├── tests/                    ← 后端测试
│   ├── Dockerfile                ← 后端容器镜像 (含 FFmpeg)
│   ├── docker-compose.yml        ← 基础编排 (6 个容器)
│   ├── docker-compose.prod.yml   ← 生产覆盖配置 (CI 当前未叠加, 见第六步说明)
│   ├── .env                      ← 实际环境变量 (不提交到 Git)
│   ├── .env.example              ← 环境变量模板
│   └── .env.production           ← 生产环境模板 (需复制为 .env)
├── ai-interview-frontend/        ← Vue 用户端前端 (Vite 构建)
│   ├── src/views/                ← 28 个页面组件
│   ├── src/api/                  ← 15 个 API 模块
│   ├── dist/                     ← 构建产物 (已提交到 Git, 服务器直接使用)
│   ├── playwright.config.js      ← E2E 测试配置
│   ├── tests/                    ← Playwright 测试
│   └── package.json
├── ai-interview-admin/           ← Vue 管理后台 (Vite 构建, base: /admin/)
│   ├── src/views/                ← 12 个后台页面
│   ├── dist/                     ← 构建产物 (已提交到 Git)
│   └── package.json
├── deploy/host-nginx/            ← 主机 Nginx 配置 (SSL 终止)
└── docs/spec/media-tools/        ← 视频工具箱完整 PRD 规范
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

### 2.3 安装 Docker Compose 插件

```bash
apt install -y docker-compose-plugin
```

### 2.4 配置安全组 (云控制台)

在阿里云控制台的安全组中放行:

| 端口 | 协议 | 用途 |
|------|------|------|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (重定向到 HTTPS) |
| 443 | TCP | HTTPS (当前已配置 SSL) |

> 不要放行 5434(PostgreSQL) 和 6379(Redis)! 生产环境 PostgreSQL 和 Redis 端口在 Docker 内部通信，不暴露到外网。
>
> 注意: 当前 `docker-compose.yml` 中 postgres 有 `5434:5432` 端口映射（绑定 0.0.0.0）。虽然安全组未放行 5434，仍建议修改 compose 去掉该映射，或至少在云安全组确认未放行。

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

# 克隆仓库 (使用 SSH 方式)
git clone git@github.com:LeonZhang778/ai-interview-shangxian.git ai-interview

# 如果服务器未配置 SSH 密钥，改用 HTTPS:
git clone https://github.com/LeonZhang778/ai-interview-shangxian.git ai-interview

# 查看目录结构
ls /home/deploy/ai-interview/
# 应该看到: ai-interview-backend/  ai-interview-frontend/  ai-interview-admin/  ...
```

> **注意**: 实际部署目录为 `/home/deploy/ai-interview`（不是 `ai-interview-shangxian`），这与 GitHub Actions 工作流 `main.yml` 中的路径保持一致。后续所有命令均以 `/home/deploy/ai-interview` 为项目根目录。

---

## 第四步: 前端构建（dist 已提交 Git, 服务器无需构建）

> **重要变更**: 本项目前端构建产物 `dist/` 已提交到 Git 仓库，`docker-compose.yml` 中 nginx 容器通过 volume 直接映射 `../ai-interview-frontend/dist` 和 `../ai-interview-admin/dist`。因此服务器 `git pull` 后**无需执行 npm install / npm run build**，前端即为最新。

### 4.1 更新前端（仅本地开发需要）

本地修改前端代码后，在开发机执行构建并提交:

```powershell
cd C:\Users\admin\Desktop\ai-interview-shangxian\ai-interview-frontend
npm install
npm run build
git add dist/
git commit -m "build: 前端构建产物"
git push
```

管理后台同理:

```powershell
cd C:\Users\admin\Desktop\ai-interview-shangxian\ai-interview-admin
npm install
npm run build
git add dist/
git commit -m "build: 后台构建产物"
git push
```

### 4.2 服务器仅需拉取代码

```bash
cd /home/deploy/ai-interview
git pull
```

### 4.3 验证

```bash
ls /home/deploy/ai-interview/ai-interview-frontend/dist/index.html
ls /home/deploy/ai-interview/ai-interview-admin/dist/index.html
# 两个文件都应该存在 (来自 Git 提交)
```

---

## 第五步: 配置生产环境 .env

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# 复制生产模板
cp .env.production .env

# 编辑 .env
vim .env
```

### 5.1 需要修改的配置

```env
# 环境
ENV=production

# 数据库 (Docker 内部通信使用服务名)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<随机强密码，使用 openssl rand -base64 16 生成>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres

# Redis (Docker 内部通信)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<随机强密码>
REDIS_CHECKPOINT_DB=0
LANGGRAPH_CHECKPOINT_TTL_MINUTES=180

# JWT 密钥 (至少 32 字节)
SECRET_KEY=<使用 openssl rand -hex 32 生成>

# 前端地址 (用于邮件验证链接和 CORS)
FRONTEND_URL=https://zhangzhengqiang.xyz

# API 端口 (与 Dockerfile 一致) + Worker 数
API_PORT=8006
API_WORKERS=2
```

> **注意**: 当前服务器实际 `POSTGRES_DB=postgres`、`POSTGRES_USER=postgres`（默认库），不是文档旧版的 `ai_interview` / `ai_user`。`FRONTEND_URL` 实际配置为 `http://8.166.120.119`（如有域名可改为 `https://zhangzhengqiang.xyz`）。

### 5.2 需要注入的凭据

| 项目 | 配置项 | 获取方式 |
|------|--------|----------|
| 通义千问 API Key | `AI_API_KEY` | https://help.aliyun.com/zh/model-studio |
| QQ 邮箱授权码 | `MAIL_PASSWORD` | QQ邮箱 → 设置 → 账户 → 开启 SMTP → 生成授权码 |
| 管理员邮箱 | `ADMIN_EMAIL` | 你自己的邮箱地址 |
| 图片生成服务 | `POLLINATIONS_API_KEY` | 图片生成 API 服务 (apihub.agnes-ai.com) 的密钥 |

推荐 AI 模型: `qwen-plus`（性价比首选）、`qwen3.7-flash`（快速）、`qwen3.7-max`（旗舰）

### 5.3 不需要修改的配置 (保持默认)

```env
# Docker 内部服务名，保持默认
POSTGRES_HOST=postgres
REDIS_HOST=redis

# AI 基础 URL (通义千问)
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-plus

# 邮件 (QQ 邮箱 SMTP)
MAIL_MAILER=smtp
MAIL_HOST=smtp.qq.com
MAIL_PORT=465
MAIL_ENCRYPTION=ssl
```

---

## 第六步: 启动所有服务

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# 一键启动 6 个容器：必须使用 CI 推送的不可变 SHA 镜像
BACKEND_IMAGE=<ACR仓库>:<commit-sha> docker compose up -d
```

> **说明**: 当前 GitHub Actions 工作流和生产服务器都使用基础 `docker-compose.yml`。该文件已经包含端口收敛、日志轮转、内存上限和 Redis Stack；`docker-compose.prod.yml` 仅保留兼容说明，不参与生产部署。

镜像拉取完成后检查:

```bash
# 查看容器状态 (应该有 6 个)
docker compose ps
```

预期输出:

```
NAME                          STATUS
ai-interview-app              Up (healthy)
ai-interview-celery-worker    Up (healthy)
ai-interview-celery-beat      Up (healthy)
ai-interview-postgres         Up (healthy)
ai-interview-redis            Up (healthy)
ai-interview-nginx            Up
```

```bash
# 查看后端日志确认无报错
docker compose logs -f app --tail 30
```

成功日志:

```
INFO:     Application starting up
INFO:     Uvicorn running on http://0.0.0.0:8006
```

### 关于 Docker 镜像

生产环境使用阿里云容器镜像服务 (ACR) 的不可变 SHA 镜像:

```
crpi-yluu2a4ik5gs0met.cn-guangzhou.personal.cr.aliyuncs.com/rwkkyyds-ai-interviews/ai-interviews-shangxian:<commit-sha>
```

`BACKEND_IMAGE` 必须显式传入；Compose 的 `ai-interview:local` fallback 只用于本地已预加载镜像，避免手动部署时静默拉取旧的 `latest`。

### 关于容器端口绑定（实测）

当前服务器实际端口绑定情况（由 CI 以基础 compose 启动）:

| 容器 | 端口绑定 |
|------|----------|
| ai-interview-app | 无对外端口（内部 app:8006） |
| ai-interview-celery-worker / beat | 无 |
| ai-interview-postgres | `0.0.0.0:5434 -> 5432` |
| ai-interview-redis | 无 |
| ai-interview-nginx | `127.0.0.1:8080 -> 8080` |

健康检查必须通过 Docker Nginx 或容器内部进行，见第九步。

---

## 第七步: 数据库迁移 & 初始化

### 7.1 数据库迁移

```bash
# 执行 Alembic 迁移 (18 个版本)
docker compose exec app alembic upgrade head
```

### 7.2 初始化系统设置

```bash
# 写入系统设置默认值 (公告、注册开关、邮件模板等)
docker compose exec app python scripts/seed_settings.py
```

### 7.3 创建管理员账号

```bash
# 创建超级管理员 (脚本内置 admin@prepwise.com / admin123)
docker compose exec app python -m app.scripts.seed_admin
```

> 注意: 首次运行创建成功后，请通过后台管理页面修改密码。老版本文档的 `scripts/create_first_admin.py` 仍存在但已不被 CI 使用，推荐统一使用 `app/scripts/seed_admin.py`（`python -m app.scripts.seed_admin`）。

---

## 第八步: 配置主机 Nginx (SSL 终止)

### 8.1 当前架构

项目采用 **双层 Nginx 架构**:

```
用户浏览器
    ↓
[主机 Nginx] (端口 80/443, SSL 终止)
    ├── 80 → 301 重定向到 HTTPS
    └── 443 → SSL 解密 → 反向代理到 Docker Nginx (:8080)
                ↓
[Docker Nginx] (容器内端口 8080, 不对外暴露)
    ├── /admin/  → 管理后台 dist
    ├── /api/    → FastAPI 后端 (app:8006)
    ├── /uploads/ → 上传文件
    ├── /health  → 健康检查
    └── /        → 用户端前端 dist
```

### 8.2 部署主机 Nginx 配置

```bash
# 复制主机 Nginx 配置
cp /home/deploy/ai-interview/deploy/host-nginx/ai-interview.conf /etc/nginx/sites-available/ai-interview

# 启用站点
ln -sf /etc/nginx/sites-available/ai-interview /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重载 Nginx
systemctl reload nginx
```

### 8.3 SSL 证书 (已配置)

域名 `zhangzhengqiang.xyz` 已通过 Let's Encrypt 配置 SSL 证书。证书路径:

```
ssl_certificate     /etc/letsencrypt/live/zhangzhengqiang.xyz/fullchain.pem
ssl_certificate_key /etc/letsencrypt/live/zhangzhengqiang.xyz/privkey.pem
```

证书自动续期 (certbot):

```bash
# 测试续期
certbot renew --dry-run

# 手动续期 (如需要)
certbot renew
```

---

## 第九步: 验证

### 健康检查 (服务器本地)

> **重要**: 当前服务器 app 容器没有对外端口映射（8006 仅容器内部），因此 `curl http://localhost:8006` 会失败。请通过以下链路验证:

```bash
# 方式一: 通过 Docker Nginx 链路 (推荐)
curl http://localhost:8080/api/v1/config/health

# 方式二: 通过主机 Nginx
curl http://8.166.120.119/api/v1/config/health
curl https://zhangzhengqiang.xyz/api/v1/config/health

# 方式三: 容器内部 (CI 使用的验证方式)
docker exec ai-interview-app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=5).status)"
```

预期返回:
```json
{"code":200,"message":"Success","data":{"status":"healthy"}}
```

### 浏览器访问

| 页面 | 地址 |
|------|------|
| 用户端 | `https://zhangzhengqiang.xyz` |
| 管理后台 | `https://zhangzhengqiang.xyz/admin/` |
| 健康检查 | `https://zhangzhengqiang.xyz/health` |
| 开发期 API 文档 | `http://8.166.120.119:8006/client/docs` (生产环境关闭) |

---

## 第十步: 后续更新流程

### 10.1 手动更新

```bash
# ---- 本地 PowerShell ----
cd C:\Users\admin\Desktop\ai-interview-shangxian
# 如修改了前端, 需先构建并提交 dist (见第四步)
git add .
git commit -m "update: 描述本次修改"
git push

# ---- 服务器 SSH ----
# 方式一: 使用部署脚本（需显式指定 CI 推送的 SHA 镜像）
cd /home/deploy/ai-interview/ai-interview-backend
BACKEND_IMAGE=<ACR仓库>:<commit-sha> bash scripts/deploy.sh

# 方式二: 手动更新
cd /home/deploy/ai-interview
git pull

# 如果改了后端代码，先让 CI 构建并推送 SHA 镜像，再在服务器显式更新
cd ai-interview-backend
BACKEND_IMAGE=<ACR仓库>:<commit-sha> docker compose pull app celery-worker celery-beat
BACKEND_IMAGE=<ACR仓库>:<commit-sha> docker compose up -d --force-recreate --no-deps app celery-worker celery-beat

# 如果改了前端代码 (dist 已提交, 仅需重启 nginx 使新 volume 生效)
docker compose restart nginx

# 如果改了数据库模型
docker compose exec app alembic upgrade head
```

### 10.2 使用 GitHub Actions 自动部署 (已配置, 推荐)

项目已配置 GitHub Actions 自动部署流水线，推送 `main` 分支后自动触发:

1. 构建 Docker 镜像并推送到阿里云 ACR (仅后端镜像, 前端 dist 已随代码提交)
2. SSH 到服务器 (部署目录 `/home/deploy/ai-interview`) 拉取代码与镜像
3. 自动备份数据库 → 重建 postgres/redis → 启动 app → 迁移 → worker/beat → nginx
4. 执行 3 层健康检查 (前端 / 后台 / API), 失败则退出并保留现场日志

### 10.3 部署脚本说明

`ai-interview-backend/scripts/deploy.sh` 提供基于不可变镜像的手动部署:

```bash
cd /home/deploy/ai-interview/ai-interview-backend
BACKEND_IMAGE=<ACR仓库>:<commit-sha> bash scripts/deploy.sh
```

脚本流程:
1. 拉取显式指定的 ACR SHA 镜像
2. 启动 PostgreSQL 和 Redis Stack
3. 重建 app 并在容器内执行健康检查
4. 执行数据库迁移，再更新 worker/beat/nginx
5. 输出容器状态并再次执行容器内健康检查

---

## 第十一步: 项目模块说明

### 11.1 核心功能模块

| 模块 | 前端页面 | 后端服务 | 说明 |
|------|----------|----------|------|
| 面试模拟 | Interview.vue, Report.vue | interview_service.py, interview_graph.py | LangGraph 状态机驱动的 AI 面试 |
| 面经社区 | Experiences.vue, ExperienceDetail.vue | experience_service.py | 面经投稿、审核、点赞、收藏、评论 |
| 学习笔记 | LearningNotes.vue, LearningNoteDetail.vue | learning_note_service.py | 富文本笔记、AI 摘要、标签、导出 |
| 笔记本 | (集成在笔记页面) | notebook_service.py | 树形笔记本组织 |
| 通知系统 | Notifications.vue | notification_service.py | 系统通知、面试报告推送 |
| 视频工具箱 | MediaTools.vue | media/ (format_config, probe, repository) | 视频格式转换、压缩、GIF、合并、水印 |
| 图片生成 | ImageStudio.vue | image_service.py | AI 图片生成 |
| 简历上传 | ResumeUpload.vue | resume_service.py | 简历解析与分析 |
| 等待列表 | WaitingList.vue | waiting_list.py | 候补名单管理 |
| 公告系统 | Announcements.vue | announcement.py (后台) | 系统公告发布 |
| 反馈闭环 | MyFeedbacks.vue | feedback.py | 用户反馈提交与回复 |
| 分析统计 | Analysis.vue, Dashboard.vue | analytics.py | 面试数据统计 |
| 系统设置 | Settings.vue (后台) | setting_service.py | 维护模式、注册开关、游客模式 |

### 11.2 后台管理模块

| 页面 | 功能 |
|------|------|
| Dashboard.vue | 运营数据概览 |
| Users.vue | 用户管理 |
| Interviews.vue | 面试管理 |
| Experiences.vue | 面经审核管理 |
| Feedbacks.vue | 反馈管理 |
| Announcements.vue | 公告管理 |
| Settings.vue | 系统设置 (维护模式、注册开关、邮件配置) |
| AuditLogs.vue | 审计日志 |
| WaitingList.vue | 候补名单管理 |
| Admins.vue | 管理员管理 |

---

## 第十二步: 架构总览

### 12.1 Docker 容器网络

```
用户浏览器 (HTTPS)
    ↓
[主机 Nginx] 端口 80/443 (SSL 终止)
    ↓ 反向代理 (127.0.0.1:8080)
[Docker Nginx] 容器内端口 8080
    ├── / → ai-interview-frontend/dist (volume 映射)
    ├── /admin/ → ai-interview-admin/dist (volume 映射)
    ├── /api/* → FastAPI (app:8006, 内部通信)
    └── /uploads/* → 上传文件 (volume 映射)

FastAPI 后端 (app:8006)
    ├── PostgreSQL (postgres:5432, 内部通信)
    │   └── 数据持久卷: postgres-data
    ├── Redis (redis:6379, 内部通信)
    │   └── 数据持久卷: redis-data
    ├── Celery Worker (异步任务: 邮件、媒体处理)
    ├── Celery Beat (定时任务: 健康检查、示例任务)
    └── 通义千问 Qwen API (外部 API)

日志: json-file 驱动 (10MB 轮转)
上传文件: ./uploads (volume 映射, 持久化)
```

### 12.2 容器详情

| 容器名 | 镜像源 | 健康检查 | 端口绑定 (实测) |
|--------|--------|----------|------|
| ai-interview-app | ACR 或 Dockerfile 构建 | HTTP 健康检查 | 无对外端口 (内部 8006) |
| ai-interview-celery-worker | 同 app | celery ping | 无 |
| ai-interview-celery-beat | 同 app | celerybeat-schedule 文件 | 无 |
| ai-interview-postgres | postgres:16-alpine | pg_isready | 127.0.0.1:5434 → 5432 |
| ai-interview-redis | redis/redis-stack-server:7.4.0-v1 | redis-cli ping + RedisJSON + RediSearch | 无 (prod) |
| ai-interview-nginx | nginx:alpine + default.conf | 无 | 127.0.0.1:8080 → 8080 |

---

## 常用运维命令

```bash
# 进入项目目录
cd /home/deploy/ai-interview/ai-interview-backend

# 查看容器状态
docker compose ps

# 查看后端日志
docker compose logs -f app --tail 100

# 查看 Celery Worker 日志
docker compose logs -f celery-worker --tail 100

# 查看 Celery Beat 日志
docker compose logs -f celery-beat --tail 100

# 查看 Nginx 日志
docker compose logs -f nginx --tail 100

# 重启单个服务
docker compose restart app
docker compose restart celery-worker

# 重启所有服务
docker compose restart

# 进入容器
docker exec -it ai-interview-app bash
docker exec -it ai-interview-postgres psql -U postgres -d postgres

# 健康检查 (三层)
docker exec ai-interview-app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=5).status)"  # 容器内部
curl -s http://localhost:8080/api/v1/config/health                                   # Docker Nginx
curl -s https://zhangzhengqiang.xyz/api/v1/config/health                             # 主机 Nginx (公网)

# 查看磁盘
df -h

# 清理 Docker 无用资源
docker system prune -f

# 清理日志文件
truncate -s 0 /home/deploy/ai-interview/ai-interview-backend/logs/*.log

# 查看主机 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Certbot 证书续期测试
certbot renew --dry-run
```

---

## 常见问题

### Q: git push 提示 .env 被忽略

根目录 `.gitignore` 中 `.env` 默认被忽略。但 `ai-interview-backend/.gitignore` 中 `.env` 被注释掉了（保留到 Git）。

生产环境使用 `.env.production` 模板，实际的 `.env` 文件不会被提交。

### Q: 502 Bad Gateway

```bash
docker compose ps                     # 检查 app 容器是否运行
docker compose logs app --tail 30     # 看报错
docker exec ai-interview-app python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8006/api/v1/config/health', timeout=5).status)"  # 容器内测试
curl -s http://localhost:8080/api/v1/config/health  # 通过 Docker Nginx
```

### Q: 前端 404 或白屏

```bash
# 检查前端 dist 是否存在
ls /home/deploy/ai-interview/ai-interview-frontend/dist/
ls /home/deploy/ai-interview/ai-interview-admin/dist/

# 检查 Nginx 日志
docker compose logs nginx --tail 30
```

### Q: 邮件发送失败

1. QQ 邮箱授权码过期 → 重新生成并更新 `.env` 中 `MAIL_PASSWORD`
2. 重启容器: `docker compose restart app celery-worker`

### Q: 磁盘满了

```bash
docker system prune -f                          # 清理 Docker
truncate -s 0 /home/deploy/ai-interview/ai-interview-backend/logs/*.log  # 清理后端日志
find /home/deploy -name "*.pyc" -delete         # 清理 Python 缓存
journalctl --vacuum-time=7d                     # 清理系统日志
```

### Q: 媒体工具 (视频转换) 不工作

确保 Dockerfile 中安装了 FFmpeg:

```bash
docker exec ai-interview-app ffmpeg -version
docker exec ai-interview-app ffprobe -version
```

如果缺少，重新构建镜像: `docker compose up -d --build app`

### Q: Celery Worker 任务卡住

```bash
# 查看 worker 日志
docker compose logs celery-worker --tail 50

# 重启 worker
docker compose restart celery-worker

# 查看 Redis 队列积压
docker exec ai-interview-redis redis-cli -a <REDIS_PASSWORD> LLEN media_tasks
```

### Q: 数据库迁移失败

```bash
# 查看当前迁移版本
docker compose exec app alembic current

# 查看迁移历史
docker compose exec app alembic history

# 回滚一个版本
docker compose exec app alembic downgrade -1

# 重新执行迁移
docker compose exec app alembic upgrade head
```

### Q: postgres 端口 5434 对外暴露

当前 `docker-compose.yml` 中 postgres 配置了 `5434:5432` 映射（绑定 0.0.0.0），虽然云安全组未放行 5434，但仍建议修改 compose 去掉该映射:

```bash
# 编辑 docker-compose.yml, 删除 postgres 的 ports 段
# 或改为仅本地访问:
# ports:
#   - "127.0.0.1:5434:5432"
docker compose up -d --force-recreate postgres
```

### Q: app 容器没有对外端口

当前 `docker-compose.yml` 基础配置中 app 没有 `ports` 映射（8006 仅容器内部）。部署脚本和 CI 都使用容器内健康检查，不需要为 app 增加宿主机端口映射；如确需临时直连，再单独添加:

```yaml
# 在 app 服务下添加:
ports:
  - "127.0.0.1:8006:8006"
```

或通过 Docker Nginx 访问（见第九步验证方式）。

---

## 部署清单

- [ ] 本地开发完成，`git push` 到 GitHub
- [ ] 服务器安装 Docker + Docker Compose 插件
- [ ] 服务器 `git clone` 拉取代码 (前端 dist 已随 Git 提交，无需构建)
- [ ] 复制 `.env.production` 为 `.env`，填入生产配置
- [ ] `BACKEND_IMAGE=<ACR仓库>:<commit-sha> docker compose up -d`
- [ ] 数据库迁移 (`alembic upgrade head`)
- [ ] 初始化系统设置 (`seed_settings.py`)
- [ ] 创建管理员 (`python -m app.scripts.seed_admin`)
- [ ] 配置主机 Nginx (`deploy/host-nginx/ai-interview.conf`)
- [ ] SSL 证书验证有效
- [ ] 浏览器访问验证 (用户端 + 管理后台 + 健康检查)
- [ ] GitHub Actions 自动部署流水线正常

---

## 版本说明

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-08-07 | v2.1 | 对齐项目实际: 部署目录 `/home/deploy/ai-interview`、前端 dist 已提交 Git（无需服务器构建）、CI 仅用基础 docker-compose.yml、postgres 端口 5434、app 无对外端口、迁移 18 版本、新增 API_WORKERS/POLLINATIONS_API_KEY、seed_admin 路径修正、容器端口表修正 |
| 2026-08-07 | v2.0 | 全面更新: API 端口 8006, 域名 SSL, 双层 Nginx, 新模块(视频工具箱/学习笔记/通知/简历/图片生成/公告/反馈/等待列表), 通义千问 Qwen, 阿里云 ACR 镜像, GitHub Actions CI/CD, Celery 媒体队列 |
| 初始版 | v1.0 | 原始部署文档 (智谱 GLM, API 8001, 单层 Nginx, 无域名) |
