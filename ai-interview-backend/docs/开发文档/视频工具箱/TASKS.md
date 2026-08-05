# 视频工具箱工程任务清单

按依赖顺序执行，不得跳过规格引用。

- [x] T001 · 增加 `MediaFile`、`MediaTask`、`MediaEvent` 模型和迁移，参考 `02-data-model.md`。

- [x] T003 · 抽取格式、编码、码率、分辨率和帧率白名单，参考 `复用与重构清单.md`。
- [x] T004 · 实现任务创建服务和用户归属校验，参考 `04-state-machines.md`、`05-rbac.md`。
- [x] T005 · 实现 Celery 媒体 Worker、临时目录和进度写入，参考 `04-state-machines.md`。
- [x] T006 · 实现视频转换 P0 工具，参考 `01-prd.md` 的 REQ-MEDIA-001 至 REQ-MEDIA-010。
- [x] T007 · 实现视频压缩 P0 工具和三种压缩模式，参考 `01-prd.md`。
- [x] T008 · 实现提取音频和音频转换，参考来源 `项目1/electron/main.ts` 的音频编码映射。
- [x] T009 · 实现任务查询、取消、结果下载和过期清理，参考 `03-api-contract.md`。
- [x] T010 · 接入客户端路由注册和统一响应，参考 `00-context.md`。
- [x] T011 · 实现工具箱入口、通用上传组件、参数表单和任务卡片，参考 `06-ux-flows.md`。
- [x] T012 · 增加 GIF 片段处理，参考 `STORY-003-video-to-gif.md`。
- [x] T013 · 增加视频合并，参考 `STORY-004-video-merge.md`。
- [x] T014 · 增加添加水印，参考 `STORY-005-video-watermark.md`。
- [x] T015 · 实现后台任务查询、重试和终止，参考 `05-rbac.md`。
- [x] T016 · 增加事件、日志、指标和告警，参考 `07-observability.md`。
- [ ] T017 · 按 `10-test-plan.md` 完成单元、集成、E2E、负载和安全测试。
- [ ] T018 · 配置功能开关、灰度、清理和回滚演练，参考 `08-rollout.md`、`12-milestones.md`。

明确不做：移除水印、URL/M3U8 下载、二维码上传、机器码、桌面会员和原账号中心。
