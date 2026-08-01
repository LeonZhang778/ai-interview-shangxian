# STORY-003 视频转 GIF

## 故事

作为网站用户，我希望选取视频的一段并转换为 GIF，以便快速分享短动画。

## 关联需求

REQ-MEDIA-002、REQ-MEDIA-003、REQ-MEDIA-004、REQ-MEDIA-005、REQ-MEDIA-008。

## 验收条件

### 场景 1：合法片段

```gherkin
Given 用户上传视频并选择开始时间小于结束时间
When 用户选择合法帧率和尺寸并提交
Then 系统创建 GIF 任务
And 任务完成后返回可下载结果
```

### 场景 2：非法时间范围

```gherkin
Given 用户设置结束时间超过视频时长或小于开始时间
When 用户提交任务
Then 系统返回 MEDIA_OPTIONS_INVALID
And 不启动 FFmpeg
```

### 场景 3：高资源参数

```gherkin
Given 用户选择过高尺寸、帧率或片段时长
When 用户提交任务
Then 系统拒绝或按服务端上限规范化
And 返回明确的参数提示
```

## 复杂度

M。主要风险是 GIF 资源消耗和输出体积。

## 完成定义

完成时间、帧率、尺寸白名单及端到端测试。
