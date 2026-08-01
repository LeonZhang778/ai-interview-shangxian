# STORY-005 添加视频水印

## 故事

作为网站用户，我希望给视频添加图片或文字水印，以便发布前标识内容来源。

## 关联需求

REQ-MEDIA-002、REQ-MEDIA-003、REQ-MEDIA-004、REQ-MEDIA-006、REQ-MEDIA-008、REQ-MEDIA-009。

## 验收条件

### 场景 1：合法图片水印

```gherkin
Given 用户上传视频和合法图片水印
When 用户选择位置、透明度和尺寸并提交
Then 系统使用白名单滤镜生成结果
And 完成后可下载
```

### 场景 2：水印文件不合法

```gherkin
Given 用户上传非图片或超过大小限制的水印文件
When 用户提交任务
Then 系统返回 MEDIA_FORMAT_UNSUPPORTED 或 MEDIA_FILE_TOO_LARGE
And 不启动处理任务
```

### 场景 3：滤镜参数越界

```gherkin
Given 用户传入越界位置、透明度或尺寸
When 用户提交任务
Then 系统拒绝非法参数或使用服务端上限
And 不允许拼接任意滤镜表达式
```

## 复杂度

L。涉及第二输入文件、滤镜安全和输出校验。

## 完成定义

完成图片上传、参数校验、滤镜白名单、越权测试和回滚开关。
