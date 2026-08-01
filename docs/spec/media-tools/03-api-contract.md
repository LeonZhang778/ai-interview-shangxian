# 媒体工具 API 合同

## 1. 公共约定

- Base URL：`/api/v1/media-tools`。
- 认证：客户端接口使用现有 `Authorization: Bearer <access_token>`。
- 请求：JSON；上传接口使用 `multipart/form-data`。
- 成功响应沿用当前项目 `ApiResponse` 结构。
- 错误响应至少包含 `code`、`message`、`request_id`。
- 前端不传物理路径，只传 `file_id`、`task_id`。

## 2. Endpoint 表

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| POST | `/files` | 上传并探测媒体文件 | 用户 |
| GET | `/files/{file_id}` | 查询媒体元数据 | 文件拥有者 |
| DELETE | `/files/{file_id}` | 删除未被任务使用的源文件 | 文件拥有者 |
| POST | `/tasks/convert` | 格式转换、压缩、截取、提取音频、音频转换 | 用户 |
| POST | `/tasks/merge` | 多文件合并 | 用户/会员策略 |
| POST | `/tasks/gif` | 视频转 GIF | 用户/会员策略 |
| POST | `/tasks/watermark` | 添加文字或图片水印 | 用户/会员策略 |
| POST | `/tasks/redact` | 区域模糊或颜色遮挡 | 用户/会员策略 |
| GET | `/tasks/{task_id}` | 查询任务状态和结果 | 任务拥有者 |
| POST | `/tasks/{task_id}/cancel` | 取消 queued/processing 任务 | 任务拥有者 |
| POST | `/tasks/{task_id}/retry` | 重试失败任务 | 任务拥有者 |
| GET | `/tasks/{task_id}/download` | 获取短期下载地址或流式下载 | 任务拥有者 |
| GET | `/tasks` | 查询当前用户任务历史 | 用户 |
| GET | `/capabilities` | 获取格式、编码器和工具能力 | 公开/登录 |

## 3. 请求模型约定

`ConvertTaskCreate`：`file_id`、`target_format`、`tool_code`、`video_codec`、`audio_codec`、`video_bitrate`、`audio_bitrate`、`resolution`、`frame_rate`、`sample_rate`、`channels`、`start_time`、`duration`、`quality`。

`MergeTaskCreate`：`file_ids`、`target_format`、`resolution`、`frame_rate`、`sample_rate`。

`GifTaskCreate`：`file_id`、`start_time`、`duration`、`width`、`fps`、`speed`、`quality`。

`WatermarkTaskCreate`：`file_id`、`watermarks[]`。每个水印仅允许 `text` 或 `image`，包括坐标、透明度、旋转、起止时间和受控 `watermark_file_id`。

`RedactTaskCreate`：`file_id`、`areas[]`、`mode`、`fill_color`。`mode` 仅允许 `blur` 或 `fill`。

## 4. 错误码

- `media_file_too_large`：文件超过当前用户限制。
- `unsupported_media_type`：扩展名、MIME 或媒体流不支持。
- `invalid_media_content`：FFprobe 无法识别有效音视频流。
- `media_file_not_found`：文件不存在或不属于当前用户。
- `media_task_not_found`：任务不存在或不属于当前用户。
- `duplicate_media_task`：相同任务正在执行。
- `media_option_invalid`：参数不合法或超出白名单。
- `media_format_incompatible`：目标格式与编码器不兼容。
- `media_task_not_cancellable`：任务已完成或已失败。
- `media_task_retry_exhausted`：超过重试次数。
- `media_storage_unavailable`：对象存储不可用。
- `media_worker_unavailable`：媒体 worker 不可用。
- `media_processing_failed`：FFmpeg 处理失败。
- `media_download_expired`：结果已过期。
- `media_feature_disabled`：功能开关关闭。
- `internal_error`：未知服务错误。

## 5. OpenAPI 3.1 摘要

```yaml
openapi: 3.1.0
info:
  title: Media Tools API
  version: 1.0.0
servers:
  - url: /api/v1/media-tools
security:
  - bearerAuth: []
paths:
  /files:
    post:
      operationId: uploadMediaFile
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [file]
              properties:
                file:
                  type: string
                  format: binary
      responses:
        '201':
          description: File created
          content:
            application/json:
              schema: { $ref: '#/components/schemas/MediaFile' }
  /tasks/convert:
    post:
      operationId: createConvertTask
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ConvertTaskCreate' }
      responses:
        '202':
          description: Task queued
          content:
            application/json:
              schema: { $ref: '#/components/schemas/MediaTask' }
  /tasks/{task_id}:
    get:
      operationId: getMediaTask
      parameters:
        - in: path
          name: task_id
          required: true
          schema: { type: string, format: uuid }
      responses:
        '200':
          description: Task status
          content:
            application/json:
              schema: { $ref: '#/components/schemas/MediaTask' }
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
  schemas:
    ConvertTaskCreate:
      type: object
      required: [file_id, target_format]
      properties:
        file_id: { type: string, format: uuid }
        target_format: { type: string, enum: [mp4, mov, mkv, webm, mp3, wav, m4a, aac, flac, ogg] }
        tool_code: { type: string, enum: [convert, compress, trim, extract_audio, audio_convert] }
        resolution: { type: string, maxLength: 32 }
        frame_rate: { type: number, minimum: 1, maximum: 120 }
        start_time: { type: number, minimum: 0 }
        duration: { type: number, exclusiveMinimum: 0, maximum: 86400 }
    MediaFile:
      type: object
      required: [id, original_name, media_kind, size_bytes, status]
      properties:
        id: { type: string, format: uuid }
        original_name: { type: string }
        media_kind: { type: string, enum: [video, audio] }
        size_bytes: { type: integer, minimum: 1 }
        duration_seconds: { type: number, nullable: true }
        width: { type: integer, nullable: true }
        height: { type: integer, nullable: true }
        status: { type: string, enum: [active, deleted, blocked] }
    MediaTask:
      type: object
      required: [id, tool_code, status, stage, progress]
      properties:
        id: { type: string, format: uuid }
        tool_code: { type: string }
        status: { type: string, enum: [queued, processing, completed, failed, cancelled] }
        stage: { type: string }
        progress: { type: integer, minimum: 0, maximum: 100 }
        download_url: { type: string, nullable: true }
        error_code: { type: string, nullable: true }
        error_message: { type: string, nullable: true }
```
