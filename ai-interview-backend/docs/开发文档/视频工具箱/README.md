# 视频工具箱开发文档

## 文档用途

本文档包把 `C:/Users/admin/Desktop/项目1` 视频格式助手中的媒体处理能力，整理为当前 AI Interview 项目的网站工具箱接入规格。重点不是复制原项目，而是明确哪些能力可以复用、哪些必须重构、哪些暂不接入。

## 核心结论

- 可复用：FFmpeg/FFprobe 处理思路、格式和编码映射、压缩参数、音频兼容性、GIF 时间段和帧率规则、合并顺序逻辑。
- 必须重构：Electron IPC、本地路径、内存任务、Express API、MySQL 用户中心、会员额度、前端状态和下载流程。
- 暂不复用：机器码、桌面窗口、账号中心、会员支付、广告、更新器、二维码上传、URL/M3U8 下载、移除水印。

## 文档索引

- [00-context.md](./00-context.md)：来源项目、当前项目技术栈和复用原则
- [01-prd.md](./01-prd.md)：产品范围、需求和优先级
- [02-data-model.md](./02-data-model.md)：媒体文件、任务和事件模型
- [03-api-contract.md](./03-api-contract.md)：接口、错误码和 OpenAPI 摘要
- [04-state-machines.md](./04-state-machines.md)：文件与任务状态机
- [05-rbac.md](./05-rbac.md)：角色和权限边界
- [06-ux-flows.md](./06-ux-flows.md)：网站页面和用户流程
- [07-observability.md](./07-observability.md)：事件、日志、指标和告警
- [08-rollout.md](./08-rollout.md)：开关、灰度、清理和回滚
- [09-nfr-slo.md](./09-nfr-slo.md)：性能、安全、可用性和可访问性
- [10-test-plan.md](./10-test-plan.md)：测试计划
- [11-risks.md](./11-risks.md)：风险登记
- [12-milestones.md](./12-milestones.md)：里程碑和退出条件
- [复用与重构清单.md](./复用与重构清单.md)：最重要的迁移判断
- [TASKS.md](./TASKS.md)：按依赖排序的开发任务
- [AGENTS.md](./AGENTS.md)：编码 Agent 执行指南

## 用户故事

- [STORY-001-video-convert.md](./故事/STORY-001-video-convert.md)
- [STORY-002-video-compress.md](./故事/STORY-002-video-compress.md)
- [STORY-003-video-to-gif.md](./故事/STORY-003-video-to-gif.md)
- [STORY-004-video-merge.md](./故事/STORY-004-video-merge.md)
- [STORY-005-video-watermark.md](./故事/STORY-005-video-watermark.md)

## 如何使用

产品和开发先阅读 `00-context.md`、`01-prd.md`、`复用与重构清单.md`；后端按 `02` 至 `05` 实现基础设施；前端按 `06` 实现页面；最后按 `TASKS.md` 和 `10-test-plan.md` 验收。

## 版本记录

- 2026-08-01：基于 `项目1` 实际代码创建网站工具箱迁移规格，明确复用与重构边界。
