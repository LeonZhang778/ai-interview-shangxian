# STORY-004 视频合并

## 故事

作为网站用户，我希望按指定顺序合并多个视频，以便生成一个连续文件。

## 关联需求

REQ-MEDIA-001、REQ-MEDIA-002、REQ-MEDIA-003、REQ-MEDIA-007、REQ-MEDIA-008。

## 验收条件

### 场景 1：合法合并

```gherkin
Given 用户上传至少两个属于自己的兼容视频
When 用户调整顺序并提交合并
Then 系统按提交顺序处理
And 返回合并结果
```

### 场景 2：输入不足

```gherkin
Given 用户只上传一个视频
When 用户提交合并
Then 系统返回 MEDIA_OPTIONS_INVALID
And 不创建 Worker 任务
```

### 场景 3：输入格式不兼容

```gherkin
Given 多个视频编码或流结构无法安全合并
When 用户提交任务
Then 系统拒绝或先执行规范化转码
And 返回明确结果，不标记为成功
```

## 复杂度

L。涉及多文件临时管理、顺序、兼容性和空间峰值。

## 完成定义

完成合并策略、空间限制、清理和集成测试。
