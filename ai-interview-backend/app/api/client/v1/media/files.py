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
from app.api.rate_limit import make_rate_limiter
from app.models.user import User
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import APIException, NotFoundError
from app.services.common.setting_service import get_setting, get_setting_bool
from app.services.media import (
    ffprobe_service,
    format_config,
    MediaFileRepository,
)
from app.services.media.observability import log_media_event, log_media_metric
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 上传限流：10 次/60 秒（超出返回 429，绝不用 403，避免前端把用户踢下线）
check_media_upload_rate_limit = make_rate_limiter("media_upload", 10, 60)

# MediaFile.original_name 是 String(255)；入库前截断到 200 字符（保留扩展名），
# 避免 DB 报错并把数据库原文回显给用户。
FILENAME_MAX_LEN = 200

# 每用户存储配额默认值（MB）；设置项 media_user_quota_mb 读不到/非法时回落该值。
DEFAULT_USER_QUOTA_MB = 2048


def parse_positive_int(raw, default: int) -> int:
    """解析正整数设置值；空值/非法值/非正数一律回落默认值，不抛异常。"""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


def truncate_filename(name: str, limit: int = FILENAME_MAX_LEN) -> str:
    """截断过长文件名并保留扩展名（纯函数，便于测试）。"""
    name = name or "unknown"
    if len(name) <= limit:
        return name
    if "." in name:
        base, ext = name.rsplit(".", 1)
        ext = "." + ext
    else:
        base, ext = name, ""
    if len(ext) >= limit:
        return name[:limit]
    return base[: limit - len(ext)] + ext


# 已知媒体容器签名：(签名, 偏移)
_MEDIA_SIGNATURES = (
    (b"\x1a\x45\xdf\xa3", 0),      # mkv/webm
    (b"FLV", 0),
    (b"ID3", 0),                   # mp3（ID3v2）
    (b"fLaC", 0),
    (b"OggS", 0),
    (b"\x89PNG\r\n\x1a\n", 0),     # png
    (b"\xff\xd8\xff", 0),          # jpeg
    (b"GIF87a", 0),
    (b"GIF89a", 0),
)

# 明确不属于媒体容器的签名：PE / ELF / ZIP
_NON_MEDIA_SIGNATURES = (
    (b"MZ", 0),
    (b"\x7fELF", 0),
    (b"PK\x03\x04", 0),
)


def classify_media_signature(header: bytes) -> str:
    """轻量魔数判定（纯函数）：返回 "media" / "non_media" / "unknown"。

    只拦截「明确不属于媒体容器」的内容（可执行/压缩包/纯文本），
    无法识别的封装头返回 unknown 放行，避免误杀合法变体。
    """
    if not header:
        return "unknown"
    # mp4/mov：偏移 4 处为 ftyp
    if header[4:8] == b"ftyp":
        return "media"
    # RIFF 家族：第 8 字节后为 AVI / WAVE / WEBP
    if header[:4] == b"RIFF" and header[8:12] in (b"AVI ", b"WAVE", b"WEBP"):
        return "media"
    # mp3 帧同步 / ADTS（aac）
    if len(header) >= 2 and header[0] == 0xFF and header[1] in (0xFB, 0xF3, 0xF2, 0xF1, 0xF9):
        return "media"
    # ASF（wma/wmv）：头部 GUID 前 4 字节
    if header[:4] == b"\x30\x26\xb2\x75":
        return "media"
    for sig, off in _MEDIA_SIGNATURES:
        if header[off:off + len(sig)] == sig:
            return "media"
    for sig, off in _NON_MEDIA_SIGNATURES:
        if header[off:off + len(sig)] == sig:
            return "non_media"
    # 纯文本：前 16 字节全是可打印 ASCII / 常见空白
    if all(b in (0x09, 0x0A, 0x0D) or 0x20 <= b <= 0x7E for b in header):
        return "non_media"
    return "unknown"


def check_quota_overflow(used_bytes: int, incoming_bytes: int, quota_mb: int) -> Optional[str]:
    """配额判定纯函数：超限返回 400 文案，未超限返回 None。"""
    quota_bytes = quota_mb * 1024 * 1024
    projected = used_bytes + incoming_bytes
    if projected <= quota_bytes:
        return None
    used_mb = projected // (1024 * 1024)
    return f"存储空间不足：已用 {used_mb}MB / 上限 {quota_mb}MB，请先删除旧文件"


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
    # 1. 功能开关检查（业务开关用 400 而非 403：前端 401/403 拦截器会 logout 踢下线）
    enabled = await get_setting_bool("media_tools_enabled", True)
    if not enabled:
        raise APIException(
            code=10400,
            message="媒体工具功能已关闭",
            status_code=400,
        )

    # 上传限流：10 次/60 秒，超出 429（Redis 不可用时沿用 fail-open）
    await check_media_upload_rate_limit(current_user)

    # 2. 文件校验
    raw_name = file.filename or "unknown"
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""

    if not ext or ext not in format_config.get_allowed_extensions():
        raise APIException(
            code=10401,
            message=f"不支持的媒体格式: {ext}",
            status_code=400,
        )

    # 入库前截断文件名（保留扩展名），避免 DB 长度报错并回显内部信息
    original_name = truncate_filename(raw_name)

    # 大小限制。分块读取，避免超大上传一次性占满进程内存。
    max_size_mb = parse_positive_int(
        await get_setting("media_file_max_size_mb", str(settings.MEDIA_MAX_FILE_SIZE_MB)),
        settings.MEDIA_MAX_FILE_SIZE_MB,
    )
    max_size_bytes = max_size_mb * 1024 * 1024

    # 3. 保存到临时目录
    upload_dir = os.path.join(settings.MEDIA_UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名，防止冲突
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    temp_path = os.path.join(upload_dir, unique_name)

    file_size = 0
    try:
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > max_size_bytes:
                    raise APIException(
                        code=10402,
                        message=f"文件大小超过限制 ({max_size_mb}MB)",
                        status_code=413,
                    )
                f.write(chunk)

        if file_size == 0:
            raise APIException(code=10401, message="不能上传空文件", status_code=400)

        # 存储配额：按实际写盘大小做最终校验（超限返回 400，不踢登录）
        quota_mb = parse_positive_int(
            await get_setting("media_user_quota_mb", str(DEFAULT_USER_QUOTA_MB)),
            DEFAULT_USER_QUOTA_MB,
        )
        used_bytes = await MediaFileRepository.sum_user_usage(db, current_user.id)
        quota_message = check_quota_overflow(used_bytes, file_size, quota_mb)
        if quota_message:
            raise APIException(code=10402, message=quota_message, status_code=400)

        # 上传魔数校验：只拦「明确非媒体」（改后缀的文本/可执行/压缩包），无法判定放行
        with open(temp_path, "rb") as probe_fh:
            header = probe_fh.read(16)
        verdict = classify_media_signature(header)
        if verdict == "non_media":
            raise APIException(
                code=10401,
                message="文件内容与扩展名不符，请上传真实的音视频/图片文件",
                status_code=400,
            )
        if verdict == "unknown":
            logger.warning("无法识别的媒体封装头，放行交由 ffprobe 判定: name=%s", original_name)

    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

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
        log_media_event(
            event="media.file.uploaded",
            file_id=record.id,
            user_id=current_user.id,
            extra={
                "media_type": record.media_type,
                "format": record.source_format,
                "size_bytes": record.size_bytes,
            },
        )
        log_media_metric("media_storage_bytes", record.size_bytes, {"media_type": record.media_type, "format": record.source_format})

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
    log_media_event(
        event="media.file.cleaned",
        file_id=file_id,
        user_id=current_user.id,
        extra={"reason": "user_delete"},
        level="info",
    )
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
    # 覆盖 format_config 里的硬编码默认值，与上传实际校验保持一致
    caps["max_file_size_mb"] = parse_positive_int(
        await get_setting("media_file_max_size_mb", str(settings.MEDIA_MAX_FILE_SIZE_MB)),
        settings.MEDIA_MAX_FILE_SIZE_MB,
    )
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
        log_media_metric("media_download_403_total", 1, {"resource": "file_raw"})
        raise NotFoundError(message="文件不存在")

    if record.expires_at and record.expires_at < datetime.now(timezone.utc):
        raise APIException(code=10414, message="文件已过期", status_code=410)

    file_path = record.storage_key
    if not os.path.exists(file_path):
        raise NotFoundError(message="文件已从磁盘移除")

    media_type = format_config.get_mime_type(record.source_format)
    log_media_event(
        event="media.result.downloaded",
        file_id=record.id,
        user_id=current_user.id,
        extra={"bytes": record.size_bytes, "format": record.source_format},
    )
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=record.original_name,
    )
