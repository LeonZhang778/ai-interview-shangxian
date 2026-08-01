"""
媒体任务 API：创建转换任务、查询、取消、重试、下载

复用 get_current_user、ApiResponse、APIException 和 setting_service。
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import APIException, NotFoundError
from app.services.common.setting_service import get_setting_bool
from app.services.media import (
    MediaFileRepository,
    MediaTaskRepository,
    MediaEventRepository,
    format_config,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tasks/convert", status_code=202)
async def create_convert_task(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建媒体转换/压缩/截取/提取音频任务。

    请求体：
    {
        "file_id": 1,
        "target_format": "mp4",
        "tool_code": "convert",     # convert / compress / trim / extract_audio / audio_convert
        "video_codec": "",          # 可选
        "audio_codec": "",          # 可选
        "video_bitrate": "",        # 可选
        "audio_bitrate": "",        # 可选
        "resolution": "",           # 可选，如 "720p" 或 "1280x720"
        "frame_rate": 0,            # 可选
        "sample_rate": 0,           # 可选
        "channels": 0,              # 可选
        "start_time": 0,            # 可选，截取起始时间(秒)
        "duration": 0,              # 可选，截取时长(秒)
        "quality": "medium"         # 可选，压缩质量
    }
    """
    # 1. 功能开关检查
    enabled = await get_setting_bool("media_tools_enabled", True)
    if not enabled:
        raise APIException(code=10400, message="媒体工具功能已关闭", status_code=403)

    # 2. 参数校验
    file_id = data.get("file_id")
    target_format = data.get("target_format", "").lower()
    tool_code = data.get("tool_code", "convert")

    if not file_id:
        raise APIException(code=10401, message="缺少 file_id", status_code=400)
    if not target_format or not format_config.is_valid_format(target_format):
        raise APIException(code=10401, message=f"不支持的目标格式: {target_format}", status_code=400)
    if tool_code not in format_config.TOOL_CODES:
        raise APIException(code=10401, message=f"不支持的工具代码: {tool_code}", status_code=400)

    # 3. 检查文件
    file_record = await MediaFileRepository.get_by_id(db, file_id, current_user.id)
    if not file_record:
        raise NotFoundError(message="文件不存在")

    # 4. 检查重复任务
    input_file_ids = [file_id]
    options = {
        "target_format": target_format,
        "tool_code": tool_code,
        "video_codec": data.get("video_codec", ""),
        "audio_codec": data.get("audio_codec", ""),
        "video_bitrate": data.get("video_bitrate", ""),
        "audio_bitrate": data.get("audio_bitrate", ""),
        "resolution": data.get("resolution", ""),
        "frame_rate": data.get("frame_rate", 0),
        "sample_rate": data.get("sample_rate", 0),
        "channels": data.get("channels", 0),
        "start_time": data.get("start_time", 0),
        "duration": data.get("duration", 0),
        "quality": data.get("quality", "medium"),
    }

    # 5. 创建任务
    task = await MediaTaskRepository.create(
        db=db,
        user_id=current_user.id,
        tool_name=tool_code,
        input_file_ids=input_file_ids,
        options_json=options,
    )

# 6. 记录事件
    await MediaEventRepository.create(
        db=db,
        task_id=task.id,
        user_id=current_user.id,
        event_name="task_created",
        payload_json={"tool_code": tool_code, "target_format": target_format},
    )

    # 7. 异步提交到 Celery 媒体队列
    try:
        from app.schedule.jobs.media_tasks import process_media_task
        process_media_task.delay(task.id)
    except Exception as e:
        logger.warning(f"Celery 任务提交失败（任务已创建，可手动重试）: {e}")

    return ApiResponse.success(
        data={
            "task_id": task.id,
            "tool_code": task.tool_name,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        },
        message="任务已创建",
        http_code=202,
    )


@router.get("/tasks/{task_id}")
async def get_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询任务状态和结果"""
    task = await MediaTaskRepository.get_by_id(db, task_id, current_user.id)
    if not task:
        raise NotFoundError(message="任务不存在")

    # 获取输出文件信息
    output_info = None
    if task.output_file_id:
        output_file = await MediaFileRepository.get_by_id(db, task.output_file_id, current_user.id)
        if output_file:
            output_info = {
                "id": output_file.id,
                "original_name": output_file.original_name,
                "size_bytes": output_file.size_bytes,
                "media_type": output_file.media_type,
                "source_format": output_file.source_format,
            }

    return ApiResponse.success(
        data={
            "id": task.id,
            "tool_code": task.tool_name,
            "status": task.status,
            "progress": task.progress,
            "error_code": task.error_code,
            "output_file": output_info,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        }
    )


@router.post("/tasks/{task_id}/cancel")
async def cancel_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消 queued/processing 任务"""
    await MediaTaskRepository.cancel_task(db, task_id, current_user.id)

    await MediaEventRepository.create(
        db=db, task_id=task_id, user_id=current_user.id, event_name="task_cancelled"
    )
    return ApiResponse.success(message="任务已取消")


@router.post("/tasks/{task_id}/retry")
async def retry_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重试失败任务"""
    task = await MediaTaskRepository.retry_task(db, task_id, current_user.id)

    await MediaEventRepository.create(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
        event_name="task_retry",
        payload_json={"retry_count": task.retry_count},
    )
    return ApiResponse.success(
        data={
            "task_id": task.id,
            "status": task.status,
            "retry_count": task.retry_count,
        },
        message="任务已重新提交",
    )


@router.get("/tasks/{task_id}/download")
async def download_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取任务输出文件的下载地址"""
    task = await MediaTaskRepository.get_by_id(db, task_id, current_user.id)
    if not task:
        raise NotFoundError(message="任务不存在")

    if task.status != "completed":
        raise APIException(code=10400, message="任务尚未完成", status_code=400)

    if not task.output_file_id:
        raise APIException(code=10400, message="任务无输出文件", status_code=400)

    output_file = await MediaFileRepository.get_by_id(db, task.output_file_id, current_user.id)
    if not output_file:
        raise NotFoundError(message="输出文件不存在")

# 检查文件是否过期
    if output_file.expires_at and output_file.expires_at < datetime.now(timezone.utc):
        raise APIException(code=10414, message="文件已过期", status_code=410)

    # 返回本地文件路径（实际场景应使用 S3 短期签名 URL）
    return ApiResponse.success(
        data={
            "download_url": f"/api/v1/media-tools/files/{output_file.id}/raw",
            "file_name": output_file.original_name,
            "size_bytes": output_file.size_bytes,
            "expires_at": output_file.expires_at.isoformat() if output_file.expires_at else None,
        }
    )


@router.get("/tasks")
async def list_media_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    status: Optional[str] = Query(None),
    tool_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户的任务历史"""
    result = await MediaTaskRepository.list_by_user(
        db, current_user.id, page=page, size=size, status=status, tool_name=tool_code,
    )
    return ApiResponse.success(data=result)


