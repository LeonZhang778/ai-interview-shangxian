# AI-Interview（智面）项目开发交接日志

更新时间：2026-08-05
仓库：`git@github.com:LeonZhang778/ai-interview-shangxian.git`
本文件用途：面向**接手开发者**的项目交接说明，覆盖项目结构、技术栈、架构、本地开发、部署、测试与当前进度。部署与服务器相关操作见 `AI-Interview-服务器部署流程.md` 与 `AI-Interview-部署交接日志.md`。

---

## 1. 项目概况

基于大模型的 AI 面试模拟平台：用户上传 PDF 简历，AI 自动解析简历并生成针对性面试题，多轮对话模拟真实面试，实时流式输出评分评语，最终生成综合评估报告；同时提供面经分享、学习笔记、通知系统、等待名单、媒体工具箱（视频/音频转换）等扩展能力。

### 核心功能

- 简历上传与 AI 智能解析（PDF → 结构化数据）
- AI 模拟面试（多轮对话、逐题问答、SSE 流式输出）
- 实时评分与综合评估报告（可分享）
- 用户注册登录（JWT 认证）、游客模式（Guest Token）
- 面经投稿/审核/点赞/收藏/评论
- 学习笔记（富文本、笔记本树、标签、全文搜索、AI 摘要、从面试回流生成）
- 通知系统、活跃度追踪与 PV 统计
- 后台管理系统（用户、面试、面经、反馈、公告、设置、审计日志、等待名单）
- 媒体工具箱（上传/探测、转换/压缩/截取/音频提取、合并、GIF、水印、区域模糊/颜色遮挡，异步 Celery 任务）

---

## 2. 仓库结构

```
ai-interview-shangxian/
├── ai-interview-backend/          # 后端 FastAPI（Python 3.12 + async）
│   ├── app/
│   │   ├── api/client/v1/         # 用户端 API（含 media/ 媒体工具箱）
│   │   ├── api/backoffice/v1/     # 管理端 API
│   │   ├── services/              # 业务逻辑层（client / backoffice / common / media）
│   │   ├── models/                # SQLAlchemy ORM 模型
│   │   ├── schemas/               # Pydantic 请求/响应模型
│   │   ├── core/                  # 配置、安全、日志、Celery
│   │   ├── graphs/                # LangGraph 面试状态机
│   │   ├── schedule/jobs/         # Celery 任务（media_tasks 等）
│   │   ├── route/                 # 路由注册中心、中间件
│   │   └── exceptions/            # 统一异常体系
│   ├── migrations/versions/       # Alembic 迁移
│   ├── tests/                     # pytest 单元/集成测试
│   ├── scripts/                   # seed_settings、create_first_admin 等
│   ├── docker-compose.yml         # 生产编排（app/celery/postgres/redis/nginx）
│   ├── Dockerfile / Dockerfile.dev
│   └── nginx/                     # 生产 Nginx 配置
├── ai-interview-frontend/         # 用户端前端（Vue 3 + Vite + Pinia）
│   └── tests/                     # Playwright E2E
├── ai-interview-admin/            # 管理端前端（Vue 3 + Vite）
├── docs/spec/media-tools/         # 媒体工具箱完整规格包（PRD/数据模型/API/状态机/测试计划）
├── AI-Interview-项目开发交接日志.md  # 本文件
├── AI-Interview-部署交接日志.md      # 服务器部署状态交接
├── AI-Interview-服务器部署流程.md    # 部署流程文档
└── README.md                       # 部署文档（VM + Docker 场景）
```

---

## 3. 技术栈

| 模块 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.115（全异步） |
| ORM | SQLAlchemy 2.0（async + asyncpg） |
| 数据库 | PostgreSQL 16 |
| 迁移 | Alembic |
| 缓存/消息队列 | Redis（异步 RedisClient 封装） |
| 异步任务 | Celery 5.5（worker + beat，队列 `media_tasks,celery`） |
| AI | OpenAI SDK 兼容接口（Qwen/DeepSeek 等，通过 `AI_BASE_URL`/`AI_MODEL` 切换） |
| 面试编排 | LangGraph 状态机（`app/graphs/interview_graph.py`） |
| 用户端前端 | Vue 3 + Vite 5 + Pinia + Vue Router（含 Bytemd 富文本、ECharts） |
| 管理端前端 | Vue 3 + Vite |
| 测试 | pytest（后端）、Playwright（前端 E2E） |
| 容器化 | Docker Compose（生产：阿里云镜像仓库；dev：本地构建） |
| 媒体引擎 | FFmpeg / FFprobe（系统级，app 与 celery-worker 镜像内均需安装） |

---

## 4. 架构设计（约定，新代码必须遵守）

1. **三层架构**：`API 层（app/api）→ Service 层（app/services）→ Model/Repository（app/models）`，禁止在路由里写业务逻辑。
2. **双端 API**：Client API（用户端）与 Backoffice API（管理端）共享 Service 层；认证依赖统一使用 `app/api/client/deps.py` 与 `app/api/backoffice/deps.py` 中的 `get_current_user`，不得自建第二套 token 校验。
3. **统一响应**：所有接口通过 `ApiResponse.success / failed / paginate`（`app/schemas/response.py`）返回 `{code, message, data}`。
4. **统一异常**：业务异常继承 `APIException`（`app/exceptions/http_exceptions.py`），子类含 `ValidationError / AuthenticationError / AuthorizationError / NotFoundError / ServerError / ForeignKeyViolationError`。
5. **路由注册中心**：新增 API 模块只需在 `app/route/router_registry.py` 的 `CLIENT_ROUTES / BACKOFFICE_ROUTES / COMMON_ROUTES` 增加一条 `RouteConfig`，无需改动 `route.py`。
6. **命名约定**：Python 文件/字段 `snake_case`，API 路径 `kebab-case`，前端组件 `PascalCase`；用户可见文本使用中文。
7. **状态机**：面试会话、媒体任务等有状态的实体，状态流转见 `docs/spec/media-tools/04-state-machines.md` 与 `app/graphs/interview_graph.py`。
8. **配置约定**：所有环境变量经 `app/core/config.py`（pydantic-settings）读取；功能开关/系统设置通过 `app/services/common/setting_service.py` 读取（带 Redis 缓存，更新后需失效缓存）。

---

## 5. 核心模块速查

| 模块 | 位置 | 说明 |
|------|------|------|
| 认证 | `app/api/client/v1/auth.py`、`app/services/client/auth.py` | 注册/登录/刷新/登出/游客（guest） |
| 简历 | `app/api/client/v1/resume.py`、`app/services/client/resume_service.py` | PDF 上传解析 |
| 面试 | `app/api/client/v1/interview.py`、`app/services/client/interview_service.py`、`app/graphs/interview_graph.py` | 面试启动/答题/流式评分/报告 |
| 面经 | `app/api/client/v1/experience.py`、`app/services/client/experience_service.py` | 投稿/审核/点赞/收藏/评论 |
| 学习笔记 | `app/api/client/v1/learning_note.py`、`app/services/client/learning_note_service.py` | 富文本、笔记本、搜索、AI 摘要、从面试生成 |
| 通知 | `app/api/client/v1/notification.py`、`app/services/client/notification_service.py` | 站内通知 |
| 系统设置 | `app/services/common/setting_service.py`、`scripts/seed_settings.py` | 站点配置、功能开关 |
| 等待名单 | `app/api/client/v1/waiting_list.py`、`app/services/client/waiting_list.py` | 邮箱验证加入 |
| 媒体工具箱 | `app/api/client/v1/media/`、`app/services/media/`、`app/schedule/jobs/media_tasks.py` | 见第 8 节 |
| 管理后台 | `app/api/backoffice/v1/*` | 用户/面试/面经/反馈/公告/设置/审计/等待名单 |

前端页面对应：用户端 `ai-interview-frontend/src/views/`（Interview、Report、Experiences、LearningNotes、MediaTools、Profile 等）；管理端 `ai-interview-admin/src/views/`（Dashboard、Users、Interviews、Experiences、Settings 等）。

---

## 6. 本地开发环境

> Windows 本地开发使用 `ai-interview-backend/.venv`，PostgreSQL 可用 Docker 容器或本地 `.local-postgres/`（该目录**不纳入 Git**）。

### 6.1 数据库与 Redis

```powershell
# Docker 方式（推荐）
docker compose up -d postgres redis

# 或使用本地 PostgreSQL 实例（如 .local-postgres，端口 5433）
# 注意 .env 中 POSTGRES_PORT 需要与实际端口一致
```

### 6.2 后端

```powershell
cd ai-interview-backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:POSTGRES_PORT='5433'   # 与本机实际端口一致
.venv\Scripts\python.exe -m alembic upgrade head      # 执行迁移
.venv\Scripts\python.exe scripts/seed_settings.py      # 初始化系统设置
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002
```

健康检查：`http://127.0.0.1:8002/api/v1/config/health`；接口文档：`/client/docs`、`/backoffice/docs`。

### 6.3 前端

```powershell
cd ai-interview-frontend   # 用户端，端口 5173
npm install
npm run dev

cd ai-interview-admin      # 管理端
npm install
npm run dev
```

两个前端的 `vite.config.js` 通过代理把 `/api`、`/uploads` 转发到后端。

### 6.4 运行测试

```powershell
cd ai-interview-backend
.venv\Scripts\python.exe -m pytest tests -q

cd ai-interview-frontend
npm test   # Playwright E2E
```

---

## 7. 数据库与迁移

- 迁移目录：`ai-interview-backend/migrations/versions/`，当前 head：`k4d5e6f7g8h9`。
- 常用命令：

```powershell
# 升级到最新
.venv\Scripts\python.exe -m alembic upgrade head
# 生成新迁移
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"
# 查看当前版本
.venv\Scripts\python.exe -m alembic current
```

- 主要数据表：`users`、`admins`、`tokens`、`admin_tokens`、`resumes`、`interviews`、`interview_messages`、`experiences`、`experience_tags`、`user_collections`、`collection_groups`、`learning_notes`、`notebooks`、`notifications`、`page_views`、`system_settings`、`waiting_list`、`media_files`、`media_tasks`、`media_events`。
- 新增表/字段必须同时提供 Alembic 迁移，迁移保持幂等（尽量使用 `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`）。
- 运行期目录（`uploads/media/`、`backups/`、`.local-postgres/`、`logs/`）不纳入 Git。

---

## 8. 媒体工具箱模块（重点）

- 规格包：`docs/spec/media-tools/`（00-context ～ 12-milestones + 故事 + TASKS.md）。
- 后端：`app/api/client/v1/media/`（files.py、tasks.py）、`app/services/media/`（repository、probe、format_config）、`app/models/media_tool.py`、`app/schedule/jobs/media_tasks.py`、`app/core/celery_app.py`。
- 前端：`ai-interview-frontend/src/views/MediaTools.vue`、`src/api/mediaTool.js`；E2E：`ai-interview-frontend/tests/media-tools.spec.js`。
- 能力：上传探测、转换/压缩/截取/音频提取、合并（2–10 文件）、GIF（时长 ≤60s、帧率 1–60、宽度 16–1920）、水印（图片、透明度、位置）、区域模糊/颜色遮挡；任务状态机 `pending → processing → completed/failed/cancelled`，进度写 Redis 并同步 PostgreSQL，事件写入 `media_events`。
- 用户归属校验：所有媒体文件/任务接口都校验 `user_id`，禁止跨用户使用（见 `app/services/media/repository.py`）。
- TASKS 进度：T001–T013 已完成，T014（P0 单测/集成/E2E）、T015（本地构建+迁移验证+媒体样本回归）进行中；T016 之后为 P1（合并/GIF/水印/红act/管理端等）。

---

## 9. 生产部署（Docker Compose）

详见 `AI-Interview-服务器部署流程.md`。要点：

```bash
# 服务器目录 /home/deploy/ai-interview/ai-interview-backend
BACKEND_IMAGE=<ACR仓库>:<commit-sha> docker compose up -d
docker compose ps        # app/postgres/redis/celery-worker/celery-beat/nginx 均健康
docker compose exec app alembic upgrade head
docker compose exec app python scripts/seed_settings.py
curl -k https://localhost/api/v1/config/health
```

- 生产镜像：阿里云个人仓库中的不可变 SHA 镜像 `crpi-yluu2a4ik5gs0met.cn-guangzhou.personal.cr.aliyuncs.com/rwkkyyds-ai-interviews/ai-interviews-shangxian:<commit-sha>`；CI/CD 通过 `BACKEND_IMAGE` 显式注入，Compose 不再默认指向远程 `latest`。
- Nginx 反代 `https://localhost` → 前端/管理端/后端；宿主机 8080 → 容器 Nginx。
- Celery worker 队列：`media_tasks,celery`；beat 负责定时任务（示例任务见 `app/schedule/celery_job.py`）。
- 健康检查：app 用 `GET /api/v1/config/health`；celery-worker 用 `celery inspect ping`。

### CI/CD

- `.github/workflows/main.yml`：GitHub Actions 推送后触发构建并远程部署（含最终 HTTPS 健康检查，避免 HTTP 301 误判；详见部署交接日志）。

---

## 10. 环境变量（.env，密钥不入库）

`ai-interview-backend/.env` 与 `.env.example`（注意 `.env` 已被 `.gitignore` 忽略）：

- `POSTGRES_USER/PASSWORD/HOST/PORT/DB`：数据库连接（生产用 `5434` 宿主映射或内部服务名 `postgres`）。
- `REDIS_HOST/PORT/PASSWORD`：Redis。
- `SECRET_KEY/ALGORITHM/ACCESS_TOKEN_EXPIRE_MINUTES/REFRESH_TOKEN_EXPIRE_DAYS`：JWT。
- `AI_API_KEY/AI_BASE_URL/AI_MODEL`：大模型 API（当前 Qwen 兼容模式）。
- `MAIL_*`：SMTP 邮件（QQ 邮箱）；`BREVO_*`：Brevo（未启用）。
- `AWS_*`：S3（未启用，当前本地存储）。
- `FRONTEND_URL`、`API_PORT`、`MEDIA_UPLOAD_DIR`、`MEDIA_MAX_FILE_SIZE_MB`、`MEDIA_RESULT_EXPIRY_HOURS` 等。

> 安全提醒：不要把 SSH 密码、GitHub Actions Secrets、数据库密码、API Key 写入仓库或交接文档。

---

## 11. 已知问题与风险

1. **本地开发环境**：IDE 终端 PTY 在 Windows 上偶发不可用（`Terminal dispatch timed out`），重载窗口（`Developer: Reload Window`）可恢复；本地 PostgreSQL 若使用 `.local-postgres/` 需确保端口 5433 服务在运行。
2. **Guest Token 依赖数据库结构**：`users.is_guest` 与 `system_settings` 表由迁移 `l5e6f7g8h9i0_add_guest_user_field.py` 提供；新环境必须先 `alembic upgrade head` 并 `seed_settings.py`，否则游客登录 500。
3. **媒体任务依赖 FFmpeg/FFprobe**：app 与 celery-worker 镜像/宿主机必须安装，否则探测与转换失败；`docs/spec/media-tools/09-nfr-slo.md` 有版本与探针要求。
4. **日志轮转**：Windows 下多进程同时写日志文件时可能触发 `PermissionError`（文件被占用），属日志系统已知边界。
5. **生产媒体转换 500 历史问题**：曾因 `FormatConfig` 缺 `TOOL_CODES` 属性报 500，已通过 `is_valid_tool_code()` 修复；后续若再遇到任务 500，优先看 `media_tasks`/`media_events` 表记录与 celery-worker 日志。

---

## 12. 交接注意事项（接手必读）

1. 开发顺序：迁移 → Repository → Service → API → 前端 → 测试 → 日志/开关，与 `docs/spec/media-tools/TASKS.md` 一致。
2. 新接口必须：复用统一响应/异常、走 RouterRegistry 注册、复用 `get_current_user`、用户可见文案中文、补测试。
3. 前端新页面必须包含加载/空/错误/成功四态，交互具备 hover/focus-visible/active/disabled 状态，移动端以 375px 为基线。
4. 提交代码前：`git status` 确认没有把 `.env`、`.local-postgres/`、`logs/`、`uploads/`、`test_media*.mp4` 等运行期文件带进仓库；`git diff --check` 检查空白错误。
5. 后端改动提交前跑 `pytest`，前端改动提交前跑 `npm run build` 与 `npm test`；部署前跑 `alembic upgrade head` 与 seed。
6. 服务器与生产环境的凭据只存在 `.env` / CI Secrets，任何交接文档不得包含明文密钥。

---

## 13. 本次提交说明（2026-08-05）

本次将以下改动连同本交接日志一起提交并推送：

- 新增 `AI-Interview-项目开发交接日志.md`（本文件）。
- 新增迁移 `ai-interview-backend/migrations/versions/l5e6f7g8h9i0_add_guest_user_field.py`（`users.is_guest`、`system_settings` 表）。
- 修改 `ai-interview-backend/app/api/client/v1/media/tasks.py`（媒体任务参数校验/工具码校验）。
- 修改 `ai-interview-backend/app/schedule/jobs/media_tasks.py`（媒体任务调度修正）。
- 新增测试 `ai-interview-backend/tests/test_media_tasks_validation.py`、`ai-interview-frontend/tests/media-tools.spec.js`。
- `.gitignore` 补充忽略本地 PostgreSQL 数据目录 `.local-postgres/`。
