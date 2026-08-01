# 媒体工具状态机

## 1. MediaFile 状态

```mermaid
stateDiagram-v2
  [*] --> uploading: POST /files
  uploading --> probing: 文件写入成功 / 触发 FFprobe
  uploading --> rejected: 大小、扩展名或 MIME 不合规
  probing --> active: 检测到有效音频或视频流 / 保存元数据
  probing --> rejected: FFprobe 失败 / 删除对象
  active --> deleted: 用户删除且无活动任务
  deleted --> [*]
  rejected --> [*]
```

约束：`rejected` 必须删除临时对象；`active` 文件被任务引用时不能物理删除。

## 2. MediaTask 状态

```mermaid
stateDiagram-v2
  [*] --> queued: 创建任务 / 写入 media_tasks
  queued --> processing: Celery worker 接收 / 写入 started_at
  queued --> cancelled: 用户取消 / 撤销 Celery 任务
  queued --> failed: worker 超时或不可用
  processing --> completed: FFmpeg 成功 + 结果上传成功 / 写 output_file_id
  processing --> failed: FFmpeg、探测或存储失败 / 删除半成品
  processing --> cancelled: 收到取消信号 / 终止子进程并清理
  failed --> queued: 用户重试且 retry_count 未超限 / 新建执行上下文
  completed --> [*]
  cancelled --> [*]
```

## 3. 阶段定义

- `upload`：接收文件。
- `probe`：读取媒体流和元数据。
- `queued`：等待 worker。
- `preparing`：校验输入和构建 FFmpeg 参数。
- `encoding`：FFmpeg 正在处理。
- `storing`：上传结果并写入数据库。
- `cleanup`：清理临时文件。

## 4. 转换规则

每次状态变化必须追加 `media_task_events`，并更新 Redis 进度。任务只有在输出对象上传成功、数据库事务提交成功后才能进入 `completed`。任何中途异常都必须先清理输出，再进入 `failed`；清理失败写日志和告警，但不得把失败任务伪装成成功。
