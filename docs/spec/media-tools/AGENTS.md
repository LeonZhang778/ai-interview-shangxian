# 媒体工具 Agent 指南

## 执行原则

严格按 `TASKS.md` 从上到下执行。产品意图以 `01-prd.md` 为准，数据以 `02-data-model.md` 为准，接口不得增加未定义的 endpoint，状态以 `04-state-machines.md` 为准，权限以 `05-rbac.md` 为准，发布以 `08-rollout.md` 为准。

## 复用与重构边界

允许提取项目1的 FFmpeg/FFprobe 纯规则、格式兼容矩阵、GIF filter 思路、合并参数统一、水印校验和清理策略。禁止整体复制 `server/index.ts`、源项目前端、源项目 OAuth/会员、MySQL 用户中心和 Electron 运行时。

## 当前项目约定

- 后端使用 FastAPI + SQLAlchemy + Alembic + Celery + Redis + PostgreSQL。
- 路由使用 `/api/v1/media-tools`，文件使用 `snake_case`，工具代码使用稳定小写字符串。
- 通过当前认证依赖 `get_current_user` 获取用户，不创建第二套登录体系。
- 路由必须加入 `app.route.router_registry.CLIENT_ROUTES`，使用 `settings.API_V1_STR` 生成 `/api/v1/media-tools` 前缀，不在模块内绕过注册中心。
- 通过 `file_id` 和 `task_id` 访问资源，不接受前端物理路径。
- 用户级查询必须带 `current_user.id`；管理员统计使用后台认证依赖并默认只返回聚合数据。
- 成功/失败响应使用 `ApiResponse`，业务异常使用 `APIException` 及其子类；不要在媒体模块创建重复响应格式。
- 功能开关、限制和保留策略使用 `setting_service`，设置变更后必须失效 Redis 设置缓存。
- Redis 进度键使用媒体专用命名空间和 TTL；Celery 媒体任务使用独立队列或显式路由。


## 安全硬规则

- 不提交密钥、Bearer token、上传媒体、转换产物、S3 签名 URL 或本地数据库。
- FFmpeg 参数必须枚举或范围校验，禁止把用户输入直接拼入 shell。
- 所有文件、任务和下载查询都必须带当前用户条件。
- FFmpeg 失败必须删除半成品，任务不能伪装为成功。
- 不把“区域模糊/遮挡”宣传为真实 AI 去水印。

## UI 规则

复用当前主站视觉、组件、主题和通知体系，不复制项目1页面。移动优先 375px；每页有 loading/empty/error/success 四态；每个交互有 hover/focus-visible/active/disabled；进度有文本和 `role=progressbar`。颜色使用项目现有 token，不硬编码主题色。

## 5. 工程自检清单

实现前必须确认以下事实：

- `CLIENT_ROUTES` 已注册媒体模块，且路由前缀来自 `settings.API_V1_STR`。
- 用户级依赖使用 `get_current_user`，查询条件包含 `current_user.id`。
- 开关、文件大小、并发和保留时长通过 `setting_service` 获取，配置更新调用 `invalidate_settings_cache`。
- Redis 进度 key 使用 `media:` 前缀并设置 TTL；Celery 任务只传 `task_id` 等 JSON 数据，不传本地路径。
- 错误响应可通过 `APIException` 的业务码、HTTP 状态码和 `data` 定位；不得新增与公共响应冲突的格式。

## 验证规则

每个任务完成后运行后端 pytest 或针对性测试，前端改动运行现有 Playwright/Vite 检查；迁移运行 Alembic 校验；媒体任务必须使用真实小样例执行一次。发现语法或结构性诊断激增时立即恢复最近检查点，不在损坏文件上继续修改。
