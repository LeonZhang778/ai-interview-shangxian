# STORY-001 视频格式转换

## 故事

作为网站用户，我希望把视频转换为常用格式，以便在不同设备或平台使用。

## 关联需求

REQ-MEDIA-001、REQ-MEDIA-002、REQ-MEDIA-003、REQ-MEDIA-004、REQ-MEDIA-005、REQ-MEDIA-006、REQ-MEDIA-007。

## 验收条件

### 场景 1：正常转换

```gherkin
Given 用户已登录并上传受支持的视频
When 用户选择 MP4 和合法编码参数并提交
Then 系统创建异步任务
And 用户可以看到处理进度
And 任务完成后可以下载结果
```

### 场景 2：格式不支持

```gherkin
Given 用户上传无法被 FFprobe 识别的文件
When 用户提交转换
Then 系统拒绝任务
And 返回 MEDIA_FORMAT_UNSUPPORTED
And 不暴露 FFmpeg 原始错误
```

### 场景 3：越权访问

```gherkin
Given 用户 A 拿到用户 B 的 task_id
When 用户 A 查询或下载该任务
Then 系统返回 MEDIA_TASK_FORBIDDEN
And 不返回文件元数据或下载地址
```

## 复杂度

L。涉及上传、格式白名单、异步 Worker、对象存储和下载鉴权。

## 完成定义

代码、迁移、单元测试、集成测试、前端流程、指标、开关和文档均完成。
