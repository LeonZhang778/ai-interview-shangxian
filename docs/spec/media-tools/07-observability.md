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

## 4. 当前后端实现约束

- API 业务异常沿用 `APIException` 的 `code/status_code/data` 字段，并通过 `get_message` 做消息本地化；媒体错误码应作为稳定业务码映射到该结构，不能仅抛出裸 `HTTPException`。
- 成功和失败响应沿用 `ApiResponse.success/failed` 的 `{code, message, data}` 契约。若需要 `request_id`，应由全局中间件或响应层统一注入，并在实现前同步更新公共响应契约。
- 功能开关、大小限制、保留期限和并发策略从 `get_setting/get_setting_bool` 读取。设置更新后调用 `invalidate_settings_cache`，避免 worker 和 API 继续使用旧策略。
- Redis 进度写入使用 `media:task:{task_id}:progress`、`media:task:{task_id}:stage` 等专用键，并设置不短于任务恢复窗口的 TTL。Redis 不可用时，数据库状态仍必须保持可追踪，禁止创建“已入队但无记录”的任务。
- Celery 任务应加入媒体专用队列或路由，避免 FFmpeg CPU 任务与邮件、图片任务互相争抢；任务参数使用 JSON 可序列化的 `task_id`，worker 重新从数据库读取并校验所有权和状态。
- 进度更新、任务事件和日志不得记录 token、密码、签名 URL、完整本地路径或用户媒体内容。

## 5. 日志格式

```text
timestamp level service event request_id user_id task_id tool_code stage progress error_code duration_ms
```

不得记录 token、密码、完整对象存储签名 URL、用户文件内容或 FFmpeg 命令中的敏感路径。

## 6. 告警

- 5 分钟内任务失败率 > 10%：通知开发负责人。
- Celery 媒体队列等待 p95 > 120 秒：通知运维。
- FFmpeg worker 无可用进程 > 2 分钟：触发高优先级告警。
- 磁盘使用率 > 80%：启动清理并通知运维；>90% 时关闭新上传开关。
- S3 写入失败率 > 5%：关闭新任务提交，保留查询和下载。
