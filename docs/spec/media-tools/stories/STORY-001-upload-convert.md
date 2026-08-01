# 媒体工具用户故事

## STORY-001：上传并转换媒体

### Story

作为综合工具平台用户，我希望上传一个视频或音频并转换为目标格式，以便在其他平台使用。

### 关联需求

REQ-MEDIA-001、REQ-MEDIA-002、REQ-MEDIA-004、REQ-MEDIA-005。

### 验收标准

```gherkin
场景: 有效视频转换为音频
  假设 用户已登录且上传有效 MP4
  当 用户选择 MP3 并提交转换
  那么 系统创建任务并显示 processing 进度
  并且 完成后提供可下载结果

场景: 损坏文件被拒绝
  假设 用户选择扩展名为 mp4 但内容损坏的文件
  当 用户上传文件
  那么 系统返回 invalid_media_content
  并且 不保留可下载对象

场景: 未登录用户提交任务
  假设 用户未登录
  当 用户点击提交
  那么 系统要求登录
  并且 不创建媒体任务
```

### UX 与遥测

复用当前主站上传和通知组件；发送 `media_file_uploaded`、`media_task_created`、`media_task_completed` 或 `media_task_failed`。

### 依赖与复杂度

依赖媒体表、任务表、Celery、Redis、S3、FFmpeg。复杂度：L。

### DoD

代码、迁移、单元测试、集成测试、E2E、错误文案、开关、日志和文档全部完成。
