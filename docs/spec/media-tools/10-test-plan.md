# 媒体工具测试计划

## 1. 单元测试

### `media_probe_service`

- Given 合法 MP4，When probe，Then 返回视频流、时长、宽高。
- Given 空文件或损坏文件，When probe，Then 返回 `invalid_media_content`。
- Given 仅音频文件，When probe，Then `has_audio=true` 且 `has_video=false`。

### `media_format_profiles`

- Given `m4a`，Then 输出格式映射为 `ipod`。
- Given 不兼容编码器，Then 回退到默认编码器。
- Given 奇数宽高，Then 输出尺寸调整为偶数。

### `media_task_service`

- Given 用户不拥有 file_id，When 创建任务，Then 返回 404 且不入队。
- Given 相同任务正在 processing，Then 返回 `duplicate_media_task`。
- Given 任务成功，Then写 output_file_id、completed_at 和进度 100。
- Given FFmpeg 失败，Then 删除半成品并写失败错误码。

## 2. 集成测试

- 上传文件 → FFprobe → PostgreSQL 记录。
- 创建任务 → Celery 入队 → Redis 进度 → PostgreSQL 完成记录。
- S3 暂时不可用时，任务失败且不泄露路径。
- 用户 A 无法读取用户 B 的文件、任务和下载结果。
- 取消 processing 任务后 FFmpeg 子进程退出并释放临时目录。

## 3. E2E

使用当前前端 Playwright 配置覆盖：

- STORY-001：上传 MP4 转 MP3 并下载。
- STORY-002：压缩视频并刷新页面恢复任务状态。
- STORY-003：上传两个视频合并并处理失败重试。
- STORY-004：添加文字水印并下载结果。

## 4. 负载测试

- 任务创建：20 RPS，持续 10 分钟，API p95 <500ms。
- 任务查询：100 RPS，持续 10 分钟，p95 <300ms。
- worker：按 1、2、4 个 worker 对比 CPU、内存、队列等待和成功率。
- 上传：分别测试 10MB、500MB、2GB 文件，不把上传带宽与 API 延迟混算。

## 5. 混沌测试

- Redis 不可用：API 返回可理解错误，不创建不可追踪任务。
- PostgreSQL 短暂断开：任务状态最终可恢复或明确失败。
- FFmpeg 进程崩溃：worker 捕获退出码、清理临时文件并重试一次。
- S3 上传失败：不把任务标为完成。
- worker 重启：queued 任务可重新消费，processing 任务按幂等策略处理。
