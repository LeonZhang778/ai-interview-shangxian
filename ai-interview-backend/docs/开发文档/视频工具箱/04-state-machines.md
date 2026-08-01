# 视频工具箱状态机

## 1. MediaFile

```mermaid
stateDiagram-v2
    [*] --> uploading: 上传开始
    uploading --> ready: 文件校验和探测成功
    uploading --> rejected: 类型/大小/病毒校验失败
    ready --> expired: 超过保留时间
    ready --> deleting: 用户删除或清理任务
    deleting --> [*]
    rejected --> [*]
    expired --> deleting: 清理任务
```

## 2. MediaTask

```mermaid
stateDiagram-v2
    [*] --> pending: 创建任务
    pending --> processing: Worker 获取任务
    pending --> cancelled: 用户取消
    processing --> completed: FFmpeg 成功且结果校验通过
    processing --> failed: FFmpeg 失败/超时/资源不足
    processing --> cancelled: 管理员终止
    failed --> pending: 管理员重试且次数未超限
    completed --> expired: 结果超过保留时间
    completed --> cancelled: 删除结果
    expired --> [*]
    cancelled --> [*]
```

## 3. 转换约束

- `pending -> processing` 必须创建 trace/span 和 Worker 记录。
- `processing -> completed` 必须完成输出文件存在性、大小、媒体类型和可读性校验。
- `processing -> failed` 只保存业务错误码，原始 stderr 进入受控日志并脱敏。
- 任务超时、Worker 重启时由 Celery 重试或标记失败，不允许长期停留在 `processing`。
