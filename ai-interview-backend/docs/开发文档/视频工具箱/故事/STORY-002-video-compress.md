# STORY-002 视频压缩

## 故事

作为网站用户，我希望选择速度、清晰度或质量优先的压缩策略，以便控制文件大小和输出效果。

## 关联需求

REQ-MEDIA-002、REQ-MEDIA-003、REQ-MEDIA-004、REQ-MEDIA-008。

## 验收条件

### 场景 1：质量优先

```gherkin
Given 用户上传合法视频
When 用户选择质量优先并提交
Then Worker 使用服务端预设参数处理
And 不允许客户端覆盖任意 FFmpeg 参数
```

### 场景 2：超出限制

```gherkin
Given 视频大小或时长超过当前配置
When 用户上传或创建任务
Then 系统拒绝请求
And 返回 MEDIA_FILE_TOO_LARGE 或 MEDIA_DURATION_LIMIT
```

### 场景 3：任务失败

```gherkin
Given FFmpeg 因输入损坏而失败
When Worker 完成失败处理
Then 任务状态为 failed
And 用户看到可理解的失败说明
And 原始 stderr 只进入脱敏日志
```

## 复杂度

L。需要资源限制、压缩预设和大文件回归。

## 完成定义

完成服务端预设、前端选择、失败处理、指标和测试。
