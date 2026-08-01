"""
媒体文件 API：上传、探测、元数据查询、删除（T007 + T008）

复用 get_current_user、ApiResponse、APIException 和 setting_service。
"""

import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.models.user import User
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import APIException, NotFoundError
from app.services.common.setting_service import get_setting, get_setting_bool
from app.services.media import (
    ffprobe_service,
    format_config,
    MediaFileRepository,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/files", status_code=201)
async def upload_media_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传并探测媒体文件。

    1. 检查功能开关 media_tools_enabled
    2. 校验文件扩展名和大小
    3. 保存到临时目录
    4. 用 ffprobe 探测媒体信息
    5. 创建 media_files 记录
    6. 返回文件元数据
    """
    # 1. 功能开关检查
    enabled = await get_setting_bool("media_tools_enabled", True)
    if not enabled:
        raise APIException(
            code=10400,
            message="媒体工具功能已关闭",
            status_code=403,
        )

    # 2. 文件校验
    original_name = file.filename or "unknown"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if not ext or ext not in format_config.get_allowed_extensions():
        raise APIException(
            code=10401,
            message=f"不支持的媒体格式: {ext}",
            status_code=400,
        )

    # 读取文件内容
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # 大小限制
    max_size_mb = int(await get_setting("media_file_max_size_mb", str(settings.MEDIA_MAX_FILE_SIZE_MB)))
    if file_size > max_size_mb * 1024 * 1024:
        raise APIException(
            code=10402,
            message=f"文件大小超过限制 ({max_size_mb}MB)",
            status_code=413,
        )

    # 3. 保存到临时目录
    upload_dir = os.path.join(settings.MEDIA_UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名，防止冲突
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join(upload_dir, unique_name)

    with open(temp_path, "wb") as f:
        f.write(file_bytes)

    try:
        # 4. 用 ffprobe 探测
        probe_info = await ffprobe_service.probe(temp_path)

        # 确定媒体类型
        media_type = format_config.get_media_kind(ext)
        if media_type == "unknown" and probe_info.has_video:
            media_type = "video"
        elif media_type == "unknown" and probe_info.has_audio:
            media_type = "audio"

        # 5. 创建数据库记录
        duration_ms = None
        if probe_info.duration_seconds is not None:
            duration_ms = int(probe_info.duration_seconds * 1000)

        record = await MediaFileRepository.create(
            db=db,
            user_id=current_user.id,
            storage_key=temp_path,  # 本地存储路径
            original_name=original_name,
            media_type=media_type,
            source_format=ext,
            size_bytes=file_size,
            duration_ms=duration_ms,
            metadata_json=probe_info.probe_summary,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.MEDIA_RESULT_EXPIRY_HOURS),
        )

        # 6. 返回结果
        return ApiResponse.success(
            data={
                "id": record.id,
                "original_name": record.original_name,
                "media_type": record.media_type,
                "source_format": record.source_format,
                "size_bytes": record.size_bytes,
                "duration_ms": record.duration_ms,
                "metadata": probe_info.probe_summary,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            },
            message="文件上传成功",
            http_code=201,
        )

    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"媒体文件探测失败: {e}", exc_info=True)
        raise APIException(
            code=10403,
            message=f"媒体文件探测失败: {str(e)}",
            status_code=400,
        )


@router.get("/files/{file_id}")
async def get_media_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询媒体文件元数据"""
    record = await MediaFileRepository.get_by_id(db, file_id, current_user.id)
    if not record:
        raise NotFoundError(message="文件不存在")

    return ApiResponse.success(
        data={
            "id": record.id,
            "original_name": record.original_name,
            "media_type": record.media_type,
            "source_format": record.source_format,
            "size_bytes": record.size_bytes,
            "duration_ms": record.duration_ms,
            "metadata": record.metadata_json,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        }
    )


@router.delete("/files/{file_id}")
async def delete_media_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除媒体文件（软删除）"""
    await MediaFileRepository.soft_delete(db, file_id, current_user.id)
    return ApiResponse.success(message="文件已删除")


@router.get("/files")
async def list_media_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    media_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询用户的媒体文件列表"""
    result = await MediaFileRepository.list_by_user(
        db, current_user.id, page=page, size=size, media_type=media_type,
    )
    return ApiResponse.success(data=result)


@router.get("/capabilities")
async def get_capabilities():
    """获取格式、编码器和工具能力（公开）"""
    caps = format_config.get_capabilities()
    return ApiResponse.success(data=caps)


@router.get("/files/{file_id}/raw")
async def download_media_file_raw(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """流式下载媒体文件原始内容"""
    record = await MediaFileRepository.get_by_id(db, file_id, current_user.id)
    if not record:
        raise NotFoundError(message="文件不存在")

    if record.expires_at and record.expires_at < datetime.now(timezone.utc):
        raise APIException(code=10414, message="文件已过期", status_code=410)

    file_path = record.storage_key
    if not os.path.exists(file_path):
        raise NotFoundError(message="文件已从磁盘移除")

    media_type = record.media_type or "application/octet-stream"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=record.original_name,
        headers={
            "Content-Disposition": f'attachment; filename="{record.original_name}"',
        },
    )