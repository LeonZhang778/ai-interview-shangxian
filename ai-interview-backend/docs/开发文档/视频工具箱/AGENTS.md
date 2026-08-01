# 视频工具箱 Agent 指南

## 执行顺序

按 `TASKS.md` 从 T001 开始执行。除非引用的规格缺失，否则不要自行增加字段、接口、角色、状态或工具。

## 真实来源

- 产品范围：`01-prd.md`
- 数据模型：`02-data-model.md`
- API：`03-api-contract.md`
- 状态机：`04-state-machines.md`
- 权限：`05-rbac.md`
- UX：`06-ux-flows.md`
- 上线：`08-rollout.md`
- 来源项目复用边界：`复用与重构清单.md`

## 强制规则

- 后端必须使用当前项目的 FastAPI、SQLAlchemy、Celery、Redis、PostgreSQL 和 JWT 体系。
- 不得复制 `项目1` 的 Electron IPC、Express 路由、MySQL 用户中心或机器码授权。
- FFmpeg 参数只允许来自服务端白名单，禁止拼接未经校验的 shell 字符串。
- 用户数据查询必须带当前用户归属条件。
- 不记录密码、token、API key、真实本地路径和原始 FFmpeg 命令。
- 前端页面重新设计，复用当前主站导航、主题、认证和通知模式。
- 每完成一个任务，更新 `TASKS.md` 并运行相关测试。
- 完成代码后运行后端测试、前端构建和必要的安全检查。

## 验收标准

- P0 工具可以上传、处理、查询进度、下载和清理。
- Worker 重启不会让任务永久卡在 processing。
- 越权任务查询和下载被拒绝。
- 失败信息脱敏，日志可关联 task_id 和 trace_id。
