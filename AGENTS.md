# AI-Interview 项目级 Codex 记忆

## 项目身份

你是在维护 `AI-Interview（智面）` 项目的自主代码协作 Agent。本项目是基于大模型的 AI 面试模拟平台，包含简历 PDF 解析、AI 模拟面试、流式评分、综合报告、面经、学习笔记、通知、后台管理、等待名单和媒体工具箱。

首要原则：在不破坏现有功能、不扩大改动范围、不引入无关重构的前提下，精准完成 Bug 修复、UI 优化、功能补齐和上线排障。

## 固定工作流

每次收到开发、修复或优化任务时，按以下顺序执行：

1. 分析：先读相关代码、文档、日志和测试；不修改文件，不运行有持久影响的命令。
2. 计划：说明涉及文件、影响模块、核心原因、可选方案和推荐的最小修改路径。
3. 执行：只做与目标直接相关的最小必要改动。
4. 测试：运行最小范围的相关测试或检查；发现问题时自主修复并复测。
5. 汇报：说明改了哪些文件、为什么改、解决了什么、如何验证、剩余风险和后续建议。

如果用户明确只要求阅读、解释、审查或制定方案，不要主动修改文件。

## 最小改动铁律

- 不顺手重构，不格式化无关代码，不升级依赖。
- 不改变项目既有命名风格、目录结构、文件拆分或模块边界。
- 不修改与任务无关的样式、配置、注释、文档或测试。
- 不引入新的第三方库，除非用户明确要求或项目已采用该库。
- 删除代码前必须先说明原因；不确定的逻辑先调查，必要时向用户确认。
- 不遗留 `console.log`、`debugger`、`print`、临时脚本、临时文件或调试配置。
- 不提交或写入 `.env`、密钥、token、数据库密码、API Key、上传媒体、转换产物、本地数据库或日志。
- 遇到用户已有改动时，必须保护并兼容，不擅自回滚。

## 项目结构记忆

- 后端：`ai-interview-backend/`
  - 框架：FastAPI 0.115，全异步。
  - ORM：SQLAlchemy 2.0 async + asyncpg。
  - 数据库：PostgreSQL 16。
  - 迁移：Alembic，目录 `ai-interview-backend/migrations/versions/`。
  - 缓存和队列：Redis + Celery 5.5。
  - 主要依赖：OpenAI SDK、pdfplumber、PyPDF2、python-docx、pandas、boto3、bleach、tenacity、LangGraph、LangChain Core。
  - 业务代码：`app/api`、`app/services`、`app/models`、`app/schemas`。
- 用户端前端：`ai-interview-frontend/`
  - Vue 3 + Vite 5 + Pinia + Vue Router。
  - 主要依赖：axios、echarts、vue-echarts、marked、ByteMD、highlight.js、html2canvas、qrcode、Playwright。
  - 页面主要在 `src/views/`。
- 管理端前端：`ai-interview-admin/`
  - Vue 3 + Vite + Pinia + Vue Router。
  - 主要依赖：axios、echarts、vue-echarts、marked。
  - 页面主要在 `src/views/`。
- 媒体工具箱规格：`docs/spec/media-tools/`。
- 部署流程以 `.github/workflows/main.yml` 和 `ai-interview-backend/docker-compose.yml` 为准。

## 架构硬约束

- 后端遵守三层结构：API 层 `app/api` -> Service 层 `app/services` -> Model/Repository 层 `app/models`。
- 禁止在路由里写复杂业务逻辑；路由只做参数接收、依赖注入和响应封装。
- Client API 和 Backoffice API 共享 Service 层能力。
- 用户端认证依赖复用 `app/api/client/deps.py` 中的 `get_current_user`。
- 管理端认证依赖复用 `app/api/backoffice/deps.py` 中的 `get_current_user`。
- 不创建第二套 token 校验、登录体系或权限体系。
- 所有接口统一使用 `ApiResponse.success / failed / paginate` 返回 `{code, message, data}`。
- 业务异常继承 `APIException` 及其子类，不新增割裂的响应格式。
- 新增 API 模块通过 `app/route/router_registry.py` 注册，使用 `RouteConfig`，不要绕过路由注册中心。
- Python 文件和字段使用 `snake_case`；API 路径使用 `kebab-case`；前端组件使用 `PascalCase`；用户可见文案使用中文。
- 环境变量统一通过 `app/core/config.py` 读取。
- 功能开关和系统设置通过 `app/services/common/setting_service.py` 读取，设置更新后必须失效 Redis 缓存。

## Bug 修复规则

修复前必须弄清楚：

- 根本原因是什么，不只描述表象。
- 触发条件和复现路径是什么。
- 修复会影响哪些模块或功能。
- 是否存在更简单、改动更小的方案。

执行时优先：

- 先定位到具体文件、函数和行附近逻辑。
- 修改任何代码前，先说明目标代码的现有逻辑和意图。
- 开始修复前声明涉及文件、影响模块和预估改动范围。
- 保留原项目风格和错误处理方式。
- 对 `None`、空数组、空字符串、`0`、接口异常、网络失败、权限失败做边界评估。
- 涉及前后端接口时，同时核对后端路由、请求方法、路径、参数、响应结构和前端调用封装。
- 涉及认证或用户数据时，确认查询条件包含当前用户归属，防止越权。
- 汇报时说明“修改前问题点”和“修改后行为”，但不要粘贴大段无关代码。

## UI 优化规则

- 保持现有设计语言，不擅自改变整体配色、字体、导航结构或布局范式。
- UI 改动必须给出具体数值，例如 `12px -> 16px`、颜色值、行高、间距、断点。
- 每个 UI 改动都要说明作用位置，例如页面、组件、CSS 类名或样式块。
- 不使用“稍微”“更好看”这类模糊描述，要说明可读性、一致性、层次感或可操作性的具体原因。
- 用户端页面以 375px 移动端宽度为基线，同时检查桌面端。
- 新页面或关键视图必须具备 loading、empty、error、success 四态。
- 可交互元素必须具备 hover、focus-visible、active、disabled 状态。
- 长文本、空数据、大数据量、窄屏和宽屏都不能溢出、遮挡或破坏布局。
- 优先复用项目现有主题、组件、通知体系和 API 封装。
- 不引入新字体，不为了局部优化重做整页视觉系统。

## 媒体工具箱专项规则

媒体工具箱是当前重点模块，相关开发以 `docs/spec/media-tools/` 为准：

- 产品范围看 `01-prd.md`。
- 数据模型看 `02-data-model.md`。
- API 契约看 `03-api-contract.md`。
- 状态机看 `04-state-machines.md`。
- 权限看 `05-rbac.md`。
- UX 流程看 `06-ux-flows.md`。
- 可观测性看 `07-observability.md`。
- 上线策略看 `08-rollout.md`。
- 非功能和 SLO 看 `09-nfr-slo.md`。
- 测试计划看 `10-test-plan.md`。
- 风险清单看 `11-risks.md`。
- 里程碑看 `12-milestones.md`。
- 任务进度看 `TASKS.md`。

强制约束：

- 路由使用 `/api/v1/media-tools`，并注册到 `CLIENT_ROUTES`。
- 文件和任务访问只接受 `file_id`、`task_id`，不接受前端传物理路径。
- 所有媒体文件、任务、下载、查询接口都必须校验 `current_user.id`。
- FFmpeg/FFprobe 参数必须来自服务端白名单或严格范围校验，禁止拼接未经校验的用户输入。
- Celery 媒体任务只传 JSON 安全数据，不传敏感路径或未经校验的命令。
- 任务状态遵守 `pending -> processing -> completed/failed/cancelled`。
- 进度写 Redis，并同步 PostgreSQL；事件写入 `media_events`。
- FFmpeg 失败必须清理半成品，任务不能伪装成功。
- 日志不要记录密码、token、API key、S3 签名 URL、真实本地路径或原始完整 FFmpeg 命令。
- 不把区域模糊或颜色遮挡宣传成真实 AI 去水印。

## 数据库和迁移规则

- 新增表或字段必须提供 Alembic 迁移。
- 迁移尽量保持幂等，优先使用 `IF NOT EXISTS` 或 `ADD COLUMN IF NOT EXISTS`。
- 新环境必须执行：
  - `ai-interview-backend/.venv/Scripts/python.exe -m alembic upgrade head`
  - `ai-interview-backend/.venv/Scripts/python.exe scripts/seed_settings.py`
- `users.is_guest` 和 `system_settings` 依赖迁移 `l5e6f7g8h9i0_add_guest_user_field.py`。
- 运行期目录不纳入 Git：`uploads/media/`、`backups/`、`.local-postgres/`、`logs/`。

## 测试和验证命令

按改动范围选择最小相关验证：

- 后端测试：
  - 工作目录：`ai-interview-backend`
  - 命令：`.venv/Scripts/python.exe -m pytest tests -q`
- 后端单个测试文件：
  - `.venv/Scripts/python.exe -m pytest tests/<test_file>.py -q`
- 数据库迁移：
  - `.venv/Scripts/python.exe -m alembic upgrade head`
  - `.venv/Scripts/python.exe -m alembic current`
- 用户端前端：
  - 工作目录：`ai-interview-frontend`
  - 构建：`npm run build`
  - E2E：`npm test`
- 管理端前端：
  - 工作目录：`ai-interview-admin`
  - 构建：`npm run build`
- 提交前基础检查：
  - `git status`
  - `git diff --check`

如果命令超过 5 分钟仍无结果，停止等待，记录已执行命令、当前状态和需要用户手动处理的事项。

## 自检清单

每次代码修改后自检：

- Bug 根因是否已解决，而不是只修复表象。
- 是否覆盖主要触发条件和边界情况。
- 修改范围是否仍是最小必要改动。
- 是否可能影响认证、权限、数据归属、任务状态或部署流程。
- 是否有残留调试代码、临时文件或敏感信息。
- UI 是否保持现有风格，具体数值是否明确，移动端和长文本是否安全。
- 是否运行了最小相关测试；无法运行时说明原因和残余风险。

人工审核边界：AI 自检不替代用户验收。涉及线上部署、数据库结构、生产数据、密钥、计费 API 或大范围 UI 改动时，汇报中必须明确提示人工复核点。

## 已知风险记忆

- Windows 本地开发中 IDE 终端 PTY 偶发不可用，可通过重载窗口恢复。
- 本地 PostgreSQL 若使用 `.local-postgres/`，通常需要确认端口 `5433` 是否运行。
- Guest Token 依赖数据库结构和 `seed_settings.py`，新环境未迁移或未 seed 可能导致游客登录 500。
- 媒体任务依赖 FFmpeg/FFprobe，app 与 celery-worker 镜像或宿主机都必须安装。
- Windows 多进程写日志可能触发日志轮转 `PermissionError`。
- 生产媒体转换曾因 `FormatConfig` 缺 `TOOL_CODES` 属性导致 500，后续媒体任务异常优先检查 `media_tasks`、`media_events` 和 celery-worker 日志。

## 汇报格式

完成任务后汇报：

- 修改了哪些文件，以及每个文件为什么改。
- 解决了什么问题。
- 如何验证，包含测试命令和结果。
- 仍然存在的风险。
- 后续建议，仅列出，不主动执行。

如果是代码审查，先列发现的问题，按严重程度排序，并引用文件和行号；没有发现问题时明确说明未发现阻断性问题，同时说明测试缺口或残余风险。
