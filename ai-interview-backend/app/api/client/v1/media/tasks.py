"""
媒体任务 API：创建转换任务、查询、取消、重试、下载

复用 get_current_user、ApiResponse、APIException 和 setting_service。
"""

import logging
import math
import re
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


_NUMBER_FIELDS = ("frame_rate", "sample_rate", "channels", "start_time", "duration")
_BITRATE_RE = re.compile(r"^[1-9][0-9]{0,5}(k|M)$", re.IGNORECASE)
_RESOLUTION_RE = re.compile(r"^[1-9][0-9]{1,4}x[1-9][0-9]{1,4}$")


def _validate_options(data: dict, target_format: str) -> None:
    video_codec = data.get("video_codec") or ""
    audio_codec = data.get("audio_codec") or ""
    if video_codec and not format_config.is_valid_codec(target_format, video_codec, "video"):
        raise APIException(code=10401, message=f"目标格式不支持视频编码器: {video_codec}", status_code=400)
    if audio_codec and not format_config.is_valid_codec(target_format, audio_codec, "audio"):
        raise APIException(code=10401, message=f"目标格式不支持音频编码器: {audio_codec}", status_code=400)

    resolution = data.get("resolution") or ""
    if resolution and resolution not in format_config.RESOLUTION_PRESETS and not _RESOLUTION_RE.fullmatch(resolution):
        raise APIException(code=10401, message="分辨率格式无效", status_code=400)

    for field in _NUMBER_FIELDS:
        value = data.get(field, 0)
        if isinstance(value, bool):
            raise APIException(code=10401, message=f"参数 {field} 必须为数字", status_code=400)
        try:
            numeric = float(value or 0)
        except (TypeError, ValueError):
            raise APIException(code=10401, message=f"参数 {field} 必须为数字", status_code=400)
        if not math.isfinite(numeric) or numeric < 0:
            raise APIException(code=10401, message=f"参数 {field} 必须为非负有限数字", status_code=400)

    if float(data.get("frame_rate", 0) or 0) > 240:
        raise APIException(code=10401, message="帧率不能超过 240", status_code=400)
    if int(float(data.get("channels", 0) or 0)) > 32:
        raise APIException(code=10401, message="声道数不能超过 32", status_code=400)
    for field in ("video_bitrate", "audio_bitrate"):
        bitrate = data.get(field) or ""
        if bitrate and not _BITRATE_RE.fullmatch(str(bitrate)):
            raise APIException(code=10401, message=f"参数 {field} 格式无效", status_code=400)


def _validate_special_options(data: dict, tool_code: str) -> None:
    if tool_code == "merge":
        file_ids = data.get("file_ids")
        if not isinstance(file_ids, list) or len(file_ids) < 2 or len(file_ids) > 10:
            raise APIException(code=10401, message="视频合并至少需要 2 个、最多 10 个文件", status_code=400)
        if any(isinstance(file_id, bool) or not isinstance(file_id, int) or file_id <= 0 for file_id in file_ids):
            raise APIException(code=10401, message="文件 ID 无效", status_code=400)
    if tool_code == "gif":
        try:
            start = float(data.get("start_time", 0) or 0)
            duration = float(data.get("duration", 0) or 0)
            frame_rate = float(data.get("frame_rate", 0) or 0)
            width = float(data.get("width", 0) or 0)
        except (TypeError, ValueError):
            raise APIException(code=10401, message="GIF 时间参数必须为数字", status_code=400)
        if not math.isfinite(start) or not math.isfinite(duration) or not math.isfinite(frame_rate) or not math.isfinite(width):
            raise APIException(code=10401, message="GIF 时间参数必须为数字", status_code=400)
        if duration <= 0 or duration > 60:
            raise APIException(code=10401, message="GIF 时长必须大于 0 且不超过 60 秒", status_code=400)
        if start < 0:
            raise APIException(code=10401, message="GIF 开始时间不能为负数", status_code=400)
        if frame_rate and not 1 <= frame_rate <= 60:
            raise APIException(code=10401, message="GIF 帧率必须在 1 到 60 之间", status_code=400)
        if width and (width < 16 or width > 1920 or width != int(width)):
            raise APIException(code=10401, message="GIF 宽度必须在 16 到 1920 像素之间", status_code=400)
        if data.get("quality", "medium") not in format_config.GIF_QUALITY:
            raise APIException(code=10401, message="GIF 质量参数无效", status_code=400)
    if tool_code == "watermark":
        watermark_file_id = data.get("watermark_file_id")
        if watermark_file_id is None:
            raise APIException(code=10401, message="缺少 watermark_file_id", status_code=400)
        if isinstance(watermark_file_id, bool) or not isinstance(watermark_file_id, int) or watermark_file_id <= 0:
            raise APIException(code=10401, message="水印文件 ID 无效", status_code=400)
        if data.get("position", "bottom-right") not in {"top-left", "top-right", "bottom-left", "bottom-right", "center"}:
            raise APIException(code=10401, message="水印位置无效", status_code=400)
        try:
            opacity = float(data.get("opacity", 1) or 0)
            width = int(data.get("watermark_width", 0) or 0)
        except (TypeError, ValueError):
            raise APIException(code=10401, message="水印透明度和宽度参数无效", status_code=400)
        if not 0 < opacity <= 1:
            raise APIException(code=10401, message="水印透明度必须在 0 到 1 之间", status_code=400)
        if width and not 16 <= width <= 1920:
            raise APIException(code=10401, message="水印宽度必须在 16 到 1920 像素之间", status_code=400)


async def _create_special_task(data: dict, tool_code: str, current_user: User, db: AsyncSession):
    enabled = await get_setting_bool("media_tools_enabled", True)
    if not enabled:
        raise APIException(code=10400, message="媒体工具功能已关闭", status_code=403)
    _validate_special_options(data, tool_code)
    file_ids = data.get("file_ids") or [data.get("file_id")]
    if not isinstance(file_ids, list) or any(isinstance(file_id, bool) or not isinstance(file_id, int) or file_id <= 0 for file_id in file_ids):
        raise APIException(code=10401, message="文件 ID 无效", status_code=400)
    records = []
    for file_id in file_ids:
        record = await MediaFileRepository.get_by_id(db, file_id, current_user.id)
        if not record:
            raise NotFoundError(message="文件不存在")
        records.append(record)
    if tool_code == "watermark":
        watermark = await MediaFileRepository.get_by_id(db, data["watermark_file_id"], current_user.id)
        if not watermark or watermark.media_type != "image":
            raise APIException(code=10401, message="水印文件必须是图片", status_code=400)
        if watermark.size_bytes > 10 * 1024 * 1024:
            raise APIException(code=10402, message="水印文件不能超过 10MB", status_code=413)
        file_ids = [file_ids[0], watermark.id]
    target_format = "gif" if tool_code == "gif" else data.get("target_format", "mp4").lower()
    if not format_config.is_valid_format(target_format):
        raise APIException(code=10401, message=f"不支持的目标格式: {target_format}", status_code=400)
    options = dict(data)
    options.update({"target_format": target_format, "tool_code": tool_code})
    task = await MediaTaskRepository.create(db, current_user.id, tool_code, file_ids, options)
    await MediaEventRepository.create(db, task.id, current_user.id, "task_created", {"tool_code": tool_code})
    try:
        from app.schedule.jobs.media_tasks import process_media_task
        result = process_media_task.delay(task.id)
        await MediaTaskRepository.update_status(db, task.id, "pending", celery_task_id=result.id)
    except Exception as exc:
        await MediaTaskRepository.update_status(db, task.id, "failed", error_code="CELERY_SUBMIT_FAILED", error_message="后台任务提交失败，请稍后重试")
        raise APIException(code=10503, message="后台任务提交失败，请稍后重试", status_code=503) from exc
    return ApiResponse.success(data={"task_id": task.id, "tool_code": tool_code, "status": task.status, "progress": task.progress}, message="任务已创建", http_code=202)


@router.post("/tasks/gif", status_code=202)
async def create_gif_task(data: dict = Body(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _create_special_task(data, "gif", current_user, db)


@router.post("/tasks/merge", status_code=202)
async def create_merge_task(data: dict = Body(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _create_special_task(data, "merge", current_user, db)


@router.post("/tasks/watermark", status_code=202)
async def create_watermark_task(data: dict = Body(...), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _create_special_task(data, "watermark", current_user, db)


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
    if not format_config.is_valid_tool_code(tool_code):
        raise APIException(code=10401, message=f"不支持的工具代码: {tool_code}", status_code=400)
    _validate_options(data, target_format)

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
        celery_result = process_media_task.delay(task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="pending",
            celery_task_id=celery_result.id,
        )
    except Exception as e:
        logger.exception("Celery 媒体任务提交失败: task_id=%s", task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="failed",
            error_code="CELERY_SUBMIT_FAILED",
            error_message="后台任务提交失败，请稍后重试",
        )
        await MediaEventRepository.create(
            db=db,
            task_id=task.id,
            user_id=current_user.id,
            event_name="task_submit_failed",
            payload_json={"error": str(e)[:200]},
        )
        raise APIException(
            code=10503,
            message="后台任务提交失败，请稍后重试",
            status_code=503,
        ) from e

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


@router.delete("/tasks/{task_id}")
async def delete_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除一条已结束的媒体任务。"""
    await MediaTaskRepository.delete_task(db, task_id, current_user.id)
    return ApiResponse.success(message="任务已删除")


@router.post("/tasks/delete-batch")
async def delete_media_tasks_batch(
    task_ids: list[int] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量删除已结束的媒体任务。"""
    normalized_ids = list(dict.fromkeys(task_ids))
    if not normalized_ids:
        raise APIException(code=10401, message="请选择要删除的任务", status_code=400)
    deleted_count = await MediaTaskRepository.delete_tasks(db, normalized_ids, current_user.id)
    return ApiResponse.success(
        data={"deleted_count": deleted_count},
        message=f"已删除 {deleted_count} 个任务",
    )


@router.post("/tasks/{task_id}/retry")
async def retry_media_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """重试失败任务"""
    task = await MediaTaskRepository.retry_task(db, task_id, current_user.id)

    try:
        from app.schedule.jobs.media_tasks import process_media_task
        celery_result = process_media_task.delay(task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="pending",
            celery_task_id=celery_result.id,
        )
    except Exception as e:
        logger.exception("Celery 媒体任务重试提交失败: task_id=%s", task.id)
        await MediaTaskRepository.update_status(
            db=db,
            task_id=task.id,
            status="failed",
            error_code="CELERY_SUBMIT_FAILED",
            error_message="后台任务重新提交失败，请稍后重试",
        )
        raise APIException(
            code=10503,
            message="后台任务重新提交失败，请稍后重试",
            status_code=503,
        ) from e

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


