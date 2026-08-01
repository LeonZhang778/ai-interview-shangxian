# 综合工具平台媒体工具模块上下文

## 1. 项目目标

当前已上线的 `ai-interview-shangxian` 作为综合工具平台的主载体，新增独立的“视频与音频工具”模块。该模块不依赖面试业务，可被普通用户作为通用在线工具使用；现有 AI 面试、学习笔记和用户中心继续保持原有边界。

源项目 `C:/Users/admin/Desktop/项目1` 的视频格式助手作为能力来源，重点蒸馏其 FFmpeg/FFprobe 规则、上传校验、格式兼容、合并、水印和任务清理逻辑。源项目的 Vue 页面、Express 主文件、MySQL 用户中心、会员支付和 Electron 桌面逻辑不直接并入。

## 2. 已确认技术栈

| 层级 | 当前主项目 | 源项目能力来源 |
|---|---|---|
| Web 前端 | Vue 3 + Vite + Vue Router | Vue 3 + TypeScript + Vite |
| API | FastAPI 0.115 + Python 3 | Express 5 + TypeScript |
| 异步任务 | Celery 5.5 + Redis | 进程内 FFmpeg 任务 Map |
| 数据库 | PostgreSQL + SQLAlchemy + Alembic | MySQL + mysql2 |
| 文件存储 | 当前项目 S3/本地上传抽象 | `uploads/` 与 `converted/` |
| 媒体引擎 | 待接入系统 FFmpeg/FFprobe | fluent-ffmpeg + FFmpeg |
| 部署 | Docker Compose、现有 Nginx、线上主站 | Web/Electron/Docker |
| 测试 | pytest、Playwright | Vitest、Playwright 脚本 |

## 3. 现有代码引用

- `ai-interview-backend/app/route/router_registry.py:1-120`：客户端路由注册中心；媒体模块应新增客户端 `RouteConfig`，由 `settings.API_V1_STR` 拼接前缀，不在业务文件内重复注册。
- `ai-interview-backend/app/route/route.py:84-160`：FastAPI 应用创建、生命周期和中间件入口。
- `ai-interview-backend/app/api/client/deps.py:1-70`：`get_current_user` 认证依赖；媒体用户级接口必须复用该依赖，不能创建第二套 token 校验。
- `ai-interview-backend/app/core/celery_app.py:1-55`：Celery broker/backend、JSON 序列化、任务超时和 worker 并发配置；媒体任务应加入独立队列或明确路由配置。
- `ai-interview-backend/app/core/config.py:1-100`：配置和环境变量入口。
- `ai-interview-backend/requirements.txt:1-51`：当前 Python 依赖。
- `ai-interview-backend/docker-compose.yml:1-110`：线上 app、Celery、Redis、PostgreSQL 编排。
- `ai-interview-backend/app/services/common/redis.py:1-170`：异步 Redis 封装；媒体进度可复用 `set_with_ttl/get`，但必须使用媒体专用 key 命名空间，不得复用限流或 LLM 缓存 key。
- `ai-interview-backend/app/services/common/setting_service.py:1-45`：系统设置读取和 Redis 缓存；功能开关、大小限制、保留时长和并发策略从此服务读取，更新后调用缓存失效。
- `ai-interview-backend/app/exceptions/http_exceptions.py:1-63`：`APIException` 及业务异常基类；媒体业务异常应映射到现有 `code/status_code/data` 结构。
- `ai-interview-backend/app/schemas/response.py:1-65`：`ApiResponse.success/failed` 统一响应；当前失败响应不自动包含 `request_id`，若媒体接口要求关联请求，应由现有中间件或响应扩展统一补充，不在单个媒体路由内伪造。
- `ai-interview-backend/app/core/security.py:1-80`：当前用户认证和 token 工具。
- `ai-interview-backend/app/utils/utils.py:22-320`：S3、文件和安全工具。

- `C:/Users/admin/Desktop/项目1/server/index.ts:650-1000`：格式、编码器、分辨率和压缩规则。
- `C:/Users/admin/Desktop/项目1/server/index.ts:1330-1470`：文字/图片水印构建。
- `C:/Users/admin/Desktop/项目1/server/index.ts:1541-1740`：视频合并任务。
- `C:/Users/admin/Desktop/项目1/server/index.ts:2651-3557`：上传、转换、水印、区域处理和进度 API。

## 4. 复用决策

### 可直接提取并改写为 Python 纯规则

- FFmpeg 输出格式别名和容器映射。
- 视频/音频编码器别名、默认值和兼容矩阵。
- FFprobe 媒体流、时长、宽高检测。
- 偶数宽高、保持比例缩放、补边和 SAR 处理。
- GIF palettegen/paletteuse 质量策略。
- 水印参数范围校验。
- 临时文件清理和失败结果删除策略。

### 必须重构

- Express 路由改为 FastAPI 路由。
- `tasks: Map` 改为 Celery + Redis + PostgreSQL。
- `inputPath/outputPath` 改为内部 `file_id/object_key`。
- MySQL 记录改为 SQLAlchemy/Alembic PostgreSQL 模型。
- 本地 `uploads/converted` 改为当前文件存储抽象，结果可落 S3。
- 会员/配额改接当前用户与平台策略，不接源项目 OAuth。

### 不迁移

- 源项目页面和 `fileStore.ts`。
- 源项目 OAuth、会员支付、MySQL 用户中心。
- Electron 主进程和安装包配置。
- `server/index.ts` 整体复制。

## 5. 命名与工程约定

Python 文件和字段使用 `snake_case`，API 路径使用 `kebab-case`，前端组件使用 `PascalCase`。新模块遵循 Router → Service → Model/Repository 分层，客户端路由挂在 `/api/v1/media-tools`。所有用户可见文本使用中文，错误通过现有 `ApiResponse` 或项目统一异常体系返回。不得把密钥、真实上传文件、转换产物或本地数据库写入 Git。

## 6. 设计系统约束

当前项目已有视觉体系优先于通用模板。媒体工具页面应复用现有 Vue 布局、主题变量、按钮、上传区域和通知组件；不复制源项目页面。移动端以 375px 为基线，必须提供加载、空、错误、成功四态；交互必须具备 hover、focus-visible、active、disabled 状态。媒体文件处理进度需要明确显示阶段、百分比、失败原因和下载操作。

## 7. 部署约束

生产部署沿用 `AI-Interview-服务器部署流程.md` 的 Docker Compose、Nginx 和现有域名入口。第一阶段不新增公网端口，媒体 API 通过主站反向代理进入 FastAPI。FFmpeg/FFprobe 必须在 app 和 celery-worker 镜像中可用，并在健康检查或启动探针中验证版本。媒体临时目录、结果文件和 S3 凭据必须使用环境变量或挂载目录配置。
