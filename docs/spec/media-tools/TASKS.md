# 媒体工具执行任务队列

按依赖顺序执行，完成一项后勾选并运行当前项目验证命令。

- [x] T001 · 确认 FFmpeg/FFprobe 版本并加入 app、celery-worker 镜像 — ref 00-context.md§7、09-nfr-slo.md§5
- [x] T002 · 新增 `media_tools_enabled`、P0/P1 开关，并接入 `setting_service` 缓存失效 — ref 08-rollout.md§1、00-context.md§3

- [x] T004 · 创建媒体 ORM Model、Repository 和用户范围查询 — ref 02-data-model.md§5、05-rbac.md§3
- [x] T005 · 实现 FFprobe 媒体探测服务 — ref 00-context.md§4、10-test-plan.md§1
- [x] T006 · 提取项目1格式别名、编码器默认值和兼容矩阵为 Python 配置 — ref 00-context.md§4、10-test-plan.md§1
- [x] T007 · 实现媒体文件上传与探测接口 `POST /api/v1/media-tools/files` — ref 03-api-contract.md§2、STORY-001
- [x] T008 · 实现文件元数据、删除和用户权限校验 — ref 03-api-contract.md§2、05-rbac.md
- [x] T009 · 实现 Celery 媒体任务基类、专用队列、Redis 进度和 PostgreSQL 状态同步 — ref 04-state-machines.md、07-observability.md、00-context.md§3

- [x] T011 · 实现任务查询、取消、重试、历史和下载接口 — ref 03-api-contract.md§2、STORY-002
- [x] T012 · 接入日志事件、trace span 和失败告警字段 — ref 07-observability.md
- [x] T013 · 新增 P0 前端工具首页和转换、压缩、音频工具页面 — ref 06-ux-flows.md§1-5
- [ ] T014 · 编写 P0 单元、集成和 E2E 测试 — ref 10-test-plan.md§1-3
- [ ] T015 · 执行本地构建、迁移验证和媒体样例回归 — ref 09-nfr-slo.md、12-milestones.md§M2
- [ ] T016 · 实现合并服务和 `POST /tasks/merge` — ref STORY-003、12-milestones.md§M3
- [ ] T017 · 实现 GIF 服务和 `POST /tasks/gif` — ref STORY-003、03-api-contract.md
- [ ] T018 · 实现水印 Schema、ASS/overlay 服务和 `POST /tasks/watermark` — ref STORY-004、11-risks.md
- [ ] T019 · 实现区域模糊/颜色遮挡 `POST /tasks/redact` — ref STORY-004、01-prd.md§4
- [ ] T020 · 实现 P1 前端页面与四态交互 — ref 06-ux-flows.md
- [ ] T021 · 实现过期文件清理、磁盘保护和管理员聚合指标 — ref 07-observability.md、11-risks.md
- [ ] T022 · 执行负载、混沌、安全和回滚演练 — ref 08-rollout.md、10-test-plan.md§4-5
- [ ] T023 · 开启预发布开关并按 1%/10%/30%/100% 放量 — ref 08-rollout.md§2
