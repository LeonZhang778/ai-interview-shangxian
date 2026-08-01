# 媒体工具可观测性

## 1. 事件

| 事件 | 触发 | 属性 | Sink | 看板 | SLO |
|---|---|---|---|---|---|
| media_file_uploaded | 文件探测成功 | user_id、file_id、kind、size、duration | 应用日志/事件表 | 上传漏斗 | 成功率 ≥99% |
| media_file_rejected | 文件校验失败 | reason、extension、mime、size | 应用日志 | 上传错误 | 错误可定位 ≥99% |
| media_task_created | 任务入队 | task_id、tool_code、format、input_count | 应用日志/DB | 任务量 | API p95 <500ms |
| media_task_started | worker 开始 | task_id、worker、queue | Celery 日志 | 队列健康 | 进入处理 ≤30秒 |
| media_task_completed | 结果写入成功 | task_id、duration_ms、input_bytes、output_bytes | 应用日志/DB | 成功率 | P0 成功率 ≥97% |
| media_task_failed | 处理失败 | task_id、error_code、ffmpeg_exit、stage | 应用日志/DB | 失败原因 | 错误码覆盖 ≥99% |
| media_task_cancelled | 用户取消 | task_id、stage、elapsed_ms | 应用日志 | 取消率 | 取消响应 ≤5秒 |
| media_result_downloaded | 结果下载 | task_id、bytes、status | 应用日志 | 下载成功率 | ≥99% |
| media_cleanup_completed | 清理任务执行 | deleted_files、bytes、errors | 定时任务日志 | 存储成本 | 清理成功 ≥99% |

## 2. 日志格式

```text
timestamp level service event request_id user_id task_id tool_code stage progress error_code duration_ms
```

不得记录 token、密码、完整对象存储签名 URL、用户文件内容或 FFmpeg 命令中的敏感路径。

## 3. Trace span

- `media.upload`
- `media.probe`
- `media.task.create`
- `media.worker.execute`
- `media.ffmpeg.spawn`
- `media.storage.put`
- `media.result.download`
- `media.cleanup`

## 4. 告警

- 5 分钟内任务失败率 > 10%：通知开发负责人。
- Celery 媒体队列等待 p95 > 120 秒：通知运维。
- FFmpeg worker 无可用进程 > 2 分钟：触发高优先级告警。
- 磁盘使用率 > 80%：启动清理并通知运维；>90% 时关闭新上传开关。
- S3 写入失败率 > 5%：关闭新任务提交，保留查询和下载。
