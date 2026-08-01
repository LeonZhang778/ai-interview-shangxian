# 视频工具箱模块上下文

## 1. 目标

本模块将 `C:/Users/admin/Desktop/项目1` 中“视频格式助手”的媒体处理能力提取到当前 AI Interview 网站，作为网站工具箱的一部分。前端页面重新设计，不直接沿用原 Electron 页面；媒体处理能力优先复用成熟的 FFmpeg 参数映射和任务流程，并改造成当前后端的 FastAPI、Celery、Redis、PostgreSQL 架构。

## 2. 来源项目分析

来源项目是 Vue 3 + TypeScript + Electron + Express + `fluent-ffmpeg` 应用，主要入口如下：

- `项目1/src/views/modules/VideoConvert.vue`：视频格式转换交互和参数组织。
- `项目1/src/views/modules/VideoCompress.vue`：压缩模式、分辨率、码率和批量设置。
- `项目1/src/views/modules/VideoMerge.vue`：视频排序、合并和输出命名。
- `项目1/src/views/modules/VideoToGif.vue`：视频片段选择、裁剪、GIF 参数。
- `项目1/src/views/modules/VideoExtractAudio.vue`：从视频提取音频。
- `项目1/src/views/modules/AudioConvert.vue`：音频格式转换和编码兼容性。
- `项目1/src/views/modules/VideoWatermark.vue`：添加与移除水印。
- `项目1/electron/main.ts`：FFmpeg/FFprobe 调用、任务进度、桌面文件系统能力。
- `项目1/server/index.ts`：Web 上传、任务创建、进度查询和下载接口。

## 3. 当前项目技术栈

- 后端：Python、FastAPI、SQLAlchemy、Alembic、PostgreSQL、Celery、Redis、S3 兼容存储。
- 客户端：Vue 3，现有 `ai-interview-frontend`。
- 路由：通过 `app/route/router_registry.py` 注册客户端和后台模块。
- 统一响应：`app/schemas/response.py`。
- 认证依赖：`app/api/client/deps.py` 及现有 JWT 体系。
- 异步任务：`app/core/celery_app.py`、`app/schedule/`。
- 当前媒体上传和文件处理能力可参考 `app/api/client/v1/image.py`、`app/services/client/image_service.py`、`app/utils/utils.py`。

## 4. 复用原则

1. 只复用媒体处理能力和经过验证的参数规则，不复用原项目的页面、品牌、Electron 窗口、机器码、会员支付和外部账号中心。
2. 所有文件路径、下载地址和任务归属改为当前项目的用户认证、临时文件和对象存储策略。
3. FFmpeg 命令必须由后端白名单参数生成，禁止客户端传入任意 shell 参数。
4. 第一阶段优先实现视频转换、压缩、提取音频、视频转 GIF；合并和水印随后接入。
5. URL 下载、二维码上传和移除水印属于高风险能力，默认关闭，完成安全评审后再开放。

## 5. 代码引用格式

本文档中的来源代码引用使用 `文件:行号` 表示，行号以分析时的来源文件为准；实现时必须重新打开文件确认最新行号。
