# 视频工具箱 API 合同

## 1. 端点

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/api/v1/media/files` | 用户 | 上传媒体文件 |
| POST | `/api/v1/media/tasks` | 用户 | 创建处理任务 |
| GET | `/api/v1/media/tasks/{task_id}` | 用户 | 查询任务 |
| GET | `/api/v1/media/tasks/{task_id}/download` | 用户 | 获取下载地址 |
| POST | `/api/v1/media/tasks/{task_id}/cancel` | 用户 | 取消任务 |
| GET | `/api/v1/media/tools` | 可选 | 获取工具和参数白名单 |
| GET | `/api/v1/backoffice/media/tasks` | 管理员 | 查询任务 |
| POST | `/api/v1/backoffice/media/tasks/{task_id}/retry` | 管理员 | 重试失败任务 |

## 2. 统一错误码

`MEDIA_FILE_TOO_LARGE`、`MEDIA_FORMAT_UNSUPPORTED`、`MEDIA_DURATION_LIMIT`、`MEDIA_QUOTA_EXCEEDED`、`MEDIA_TASK_NOT_FOUND`、`MEDIA_TASK_FORBIDDEN`、`MEDIA_TASK_NOT_CANCELLABLE`、`MEDIA_OPTIONS_INVALID`、`MEDIA_PROCESS_FAILED`、`MEDIA_DOWNLOAD_EXPIRED`、`MEDIA_STORAGE_UNAVAILABLE`、`MEDIA_WORKER_UNAVAILABLE`。

## 3. OpenAPI 摘要

```yaml
openapi: 3.1.0
info:
  title: Media Toolbox API
  version: 1.0.0
paths:
  /api/v1/media/files:
    post:
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [file]
              properties:
                file: { type: string, format: binary }
      responses:
        '201': { description: Uploaded }
        '413': { description: File too large }
  /api/v1/media/tasks:
    post:
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskCreate'
      responses:
        '202': { description: Accepted }
        '422': { description: Invalid options }
  /api/v1/media/tasks/{task_id}:
    get:
      security: [{ bearerAuth: [] }]
      parameters:
        - { name: task_id, in: path, required: true, schema: { type: string, format: uuid } }
      responses:
        '200': { description: Task status }
        '404': { description: Not found }
components:
  securitySchemes:
    bearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
  schemas:
    TaskCreate:
      type: object
      required: [tool_name, input_file_ids, options]
      properties:
        tool_name: { type: string, enum: [video-convert, video-compress, video-to-gif, extract-audio, audio-convert, video-merge, video-watermark] }
        input_file_ids: { type: array, items: { type: string, format: uuid }, minItems: 1 }
        options: { type: object, additionalProperties: true }
```

## 4. 实现约束

- 路由放在 `app/api/client/v1/media_tool.py`，后台路由放在 `app/api/backoffice/v1/media_tool.py`。
- 服务层放在 `app/services/client/media_tool_service.py`，任务执行放在 `app/schedule/jobs/media_tool.py`。
- 使用当前项目统一响应模型和认证依赖，不复制 `项目1` 的 Express 响应格式。
- 下载接口必须校验任务所属用户、状态和过期时间。
