# 媒体工具用户故事

## STORY-002：处理任务可恢复

### Story

作为用户，我希望刷新页面后仍能看到任务状态，并能对失败任务重试或取消，以便不丢失处理结果。

### 关联需求

REQ-MEDIA-004、REQ-MEDIA-006、REQ-MEDIA-007。

### 验收标准

```gherkin
场景: 刷新后恢复 processing
  假设 任务已进入 processing
  当 用户刷新任务页面
  那么 系统根据 task_id 返回最新阶段和进度
  并且 不重复创建任务

场景: 失败任务重试
  假设 任务因 FFmpeg 临时错误失败且未超过重试次数
  当 用户点击重试
  那么 系统创建新的执行上下文
  并且 原任务错误记录保留

场景: 用户取消排队任务
  假设 任务状态为 queued
  当 用户点击取消
  那么 任务进入 cancelled
  并且 worker 不再启动 FFmpeg
```

### UX 与遥测

任务页提供取消、重试、下载和删除操作；发送 `media_task_cancelled`、`media_task_failed`。

### 依赖与复杂度

依赖 Celery 任务撤销、Redis 进度和 PostgreSQL 状态机。复杂度：L。

### DoD

覆盖 worker 重启、Redis 短暂故障、重复提交和状态恢复测试。
