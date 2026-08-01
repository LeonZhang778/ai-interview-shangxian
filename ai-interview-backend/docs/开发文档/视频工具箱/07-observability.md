# 视频工具箱可观测性

## 1. 事件

| 事件 | 触发 | 关键属性 | 归属 |
|---|---|---|---|
| media.file.uploaded | 文件校验通过 | user_id, media_type, format, size_bytes | 产品/稳定性 |
| media.task.created | 任务入队 | task_id, tool_name, input_count | 产品 |
| media.task.started | Worker 开始 | task_id, queue_wait_ms | 稳定性 |
| media.task.progress | 进度更新 | task_id, percent | 稳定性 |
| media.task.completed | 输出校验通过 | task_id, duration_ms, output_size | 产品/性能 |
| media.task.failed | 任务失败 | task_id, error_code, retry_count | 稳定性 |
| media.result.downloaded | 下载成功 | task_id, user_id, bytes | 产品 |
| media.file.cleaned | 自动清理 | file_id, reason | 成本 |

## 2. 日志

结构化日志字段：`timestamp`、`level`、`service`、`trace_id`、`user_id_hash`、`task_id`、`tool_name`、`event`、`duration_ms`、`error_code`。禁止记录 token、密码、API key、完整本地路径和原始媒体内容。

## 3. 指标和告警

- `media_task_success_rate`：按工具统计成功率，低于 95% 告警。
- `media_task_duration_seconds`：按工具统计 p50/p95/p99。
- `media_queue_depth`：队列积压持续 5 分钟告警。
- `media_worker_failure_total`：Worker 启动或 FFmpeg 执行失败告警。
- `media_storage_bytes`：临时目录和对象存储增长异常告警。
- `media_download_403_total`：越权下载尝试告警。
