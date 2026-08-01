# 综合工具平台媒体工具模块

## 文档索引

- [00-context.md](./00-context.md)：项目上下文、技术栈和复用边界
- [01-prd.md](./01-prd.md)：产品目标、范围和需求编号
- [02-data-model.md](./02-data-model.md)：媒体文件、任务和事件数据模型
- [03-api-contract.md](./03-api-contract.md)：API 合同、错误码和 OpenAPI 摘要
- [04-state-machines.md](./04-state-machines.md)：文件和任务状态机
- [05-rbac.md](./05-rbac.md)：角色、资源和权限矩阵
- [06-ux-flows.md](./06-ux-flows.md)：页面清单和用户流程
- [07-observability.md](./07-observability.md)：事件、日志、指标和告警
- [08-rollout.md](./08-rollout.md)：功能开关、放量和回滚
- [09-nfr-slo.md](./09-nfr-slo.md)：性能、安全、可访问性和保留策略
- [10-test-plan.md](./10-test-plan.md)：单元、集成、E2E、负载和混沌测试
- [11-risks.md](./11-risks.md)：风险登记
- [12-milestones.md](./12-milestones.md)：里程碑和退出条件
- [TASKS.md](./TASKS.md)：按依赖排序的工程执行队列
- [AGENTS.md](./AGENTS.md)：编码 Agent 执行规则

## 用户故事

- [STORY-001-upload-convert.md](./stories/STORY-001-upload-convert.md)
- [STORY-002-task-recovery.md](./stories/STORY-002-task-recovery.md)
- [STORY-003-merge-gif.md](./stories/STORY-003-merge-gif.md)
- [STORY-004-watermark-redact.md](./stories/STORY-004-watermark-redact.md)

## 如何使用

产品、架构和运营人员先阅读 `01` 至 `12`；编码 Agent 以 `TASKS.md` 为唯一执行队列，并从 `00-context.md` 获取现有代码引用。任务完成后必须更新任务复选框并运行对应验证。

## 版本记录

- 2026-08-01：创建媒体工具模块工程规格包，确定项目1代码按“纯媒体能力复用、平台基础设施重构”接入当前主站。
