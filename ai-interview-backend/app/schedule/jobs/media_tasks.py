"""
媒体工具 Celery 后台任务（T009 + T012）

处理媒体转换、压缩、截取、音频提取等 FFmpeg 操作。
使用独立的事件循环，通过 DB 直接读写，不依赖 FastAPI 上下文。
包含结构化日志追踪（trace span）和失败告警支持。
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.media_tool import MediaFile, MediaTask, MediaEvent
from app.services.media.format_config import format_config
from app.services.media.observability import log_media_alert, log_media_event, log_media_metric

logger = logging.getLogger(__name__)

# ============================================================
# 结构化日志追踪（T012）
# 每个任务处理流程生成一个 trace_id，子步骤生成 span_id
# ============================================================

def _log_structured(
    event: str,
    task_id: int,
    trace_id: str,
    span_id: str,
    user_id: Optional[int] = None,
    extra: Optional[dict] = None,
    level: str = "info",
):
    """输出结构化日志条目，包含 trace/span 上下文"""
    safe_extra = {"span_id": span_id}
    if extra:
        safe_extra.update(extra)
    log_media_event(
        event=event,
        task_id=task_id,
        user_id=user_id,
        trace_id=trace_id,
        tool_name=safe_extra.get("tool_code") or safe_extra.get("tool_name"),
        extra=safe_extra,
        level=level,
    )


def _log_error_alert(
    task_id: int,
    trace_id: str,
    error_code: str,
    error_message: str,
    user_id: int,
    retry_count: int,
):
    """输出高优先级错误告警日志（可在日志聚合系统中触发告警规则）"""
    log_media_alert(
        "media.worker_failure_total",
        severity="high",
        task_id=task_id,
        trace_id=trace_id,
        user_id=user_id,
        error_code=error_code,
        extra={"retry_count": retry_count, "error_message": error_message[:200]},
    )


def _task_duration_ms(task: MediaTask) -> Optional[int]:
    if not task.started_at:
        return None
    finished_at = task.finished_at or datetime.now(timezone.utc)
    return int((finished_at - task.started_at).total_seconds() * 1000)


def _queue_wait_ms(task: MediaTask) -> Optional[int]:
    if not task.created_at:
        return None
    started_at = task.started_at or datetime.now(timezone.utc)
    return int((started_at - task.created_at).total_seconds() * 1000)


def _status_event_name(status: str, progress: Optional[int]) -> str:
    if status == "processing":
        return "media.task.started" if progress is not None and progress <= 5 else "media.task.progress"
    if status == "completed":
        return "media.task.completed"
    if status == "failed":
        return "media.task.failed"
    if status == "cancelled":
        return "media.task.cancelled"
    return f"media.task.{status}"

# 避免重复创建引擎，用模块级缓存
_engine = None
_session_factory = None


def _get_session_factory():
    """获取或创建异步数据库会话工厂"""
    global _engine, _session_factory
    if _session_factory is None:
        db_url = (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        _engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=5)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


async def _dispose_engine():
    """清理引擎连接池"""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def _is_task_cancelled(db, task_id: int) -> bool:
    result = await db.execute(
        select(MediaTask.status).where(MediaTask.id == task_id)
    )
    return result.scalar_one_or_none() == "cancelled"


async def _update_task_status(
    db, task_id: int, status: str, progress: Optional[int] = None,
    error_code: Optional[str] = None, error_message: Optional[str] = None,
    output_file_id: Optional[int] = None, celery_task_id: Optional[str] = None,
    trace_id: Optional[str] = None, span_id: Optional[str] = None,
):
    """更新任务状态并记录事件（T012 结构化日志）"""
    result = await db.execute(select(MediaTask).where(MediaTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return

    # 终态不可被迟到的 Worker 进度更新覆盖。
    if task.status in ("completed", "failed", "cancelled") and status != task.status:
        return

    task.status = status
    if progress is not None:
        task.progress = progress
    if error_code:
        task.error_code = error_code
    if error_message:
        task.error_message = error_message
    if output_file_id is not None:
        task.output_file_id = output_file_id
    if celery_task_id:
        task.celery_task_id = celery_task_id

    if status == "processing" and task.started_at is None:
        task.started_at = datetime.now(timezone.utc)
    if status in ("completed", "failed", "cancelled"):
        task.finished_at = datetime.now(timezone.utc)

    await db.commit()

    event_name = _status_event_name(status, progress)
    duration_ms = _task_duration_ms(task) if status in ("completed", "failed", "cancelled") else None
    queue_wait_ms = _queue_wait_ms(task) if event_name == "media.task.started" else None
    output_size = None
    if output_file_id is not None:
        output_result = await db.execute(select(MediaFile.size_bytes).where(MediaFile.id == output_file_id))
        output_size = output_result.scalar_one_or_none()

    # 结构化日志追踪
    if trace_id and span_id:
        extra = {
            "span_id": span_id,
            "stage": status,
            "queue_wait_ms": queue_wait_ms,
            "output_file_id": output_file_id,
            "output_size": output_size,
        }
        log_level = "error" if status == "failed" else "warning" if status == "cancelled" else "info"
        log_media_event(
            event=event_name,
            task_id=task_id,
            user_id=task.user_id,
            trace_id=trace_id,
            tool_name=task.tool_name,
            percent=progress,
            duration_ms=duration_ms,
            error_code=error_code,
            extra=extra,
            level=log_level,
        )
        if event_name == "media.task.started" and queue_wait_ms is not None:
            log_media_metric("media_queue_wait_seconds", queue_wait_ms / 1000, {"tool_name": task.tool_name})
        if event_name == "media.task.completed" and duration_ms is not None:
            log_media_metric("media_task_duration_seconds", duration_ms / 1000, {"tool_name": task.tool_name})
            log_media_metric("media_task_success_total", 1, {"tool_name": task.tool_name})
        if event_name == "media.task.failed":
            log_media_metric("media_worker_failure_total", 1, {"tool_name": task.tool_name, "error_code": error_code})
        # 失败告警
        if status == "failed" and error_code:
            _log_error_alert(
                task_id=task_id,
                trace_id=trace_id,
                error_code=error_code,
                error_message=error_message or "",
                user_id=task.user_id,
                retry_count=task.retry_count or 0,
            )

    # 记录事件
    event = MediaEvent(
        task_id=task_id,
        user_id=task.user_id,
        event_name=event_name,
        payload_json={
            "percent": progress,
            "error_code": error_code,
            "status": status,
            "trace_id": trace_id,
            "span_id": span_id,
            "duration_ms": duration_ms,
            "queue_wait_ms": queue_wait_ms,
            "output_size": output_size,
        },
    )
    db.add(event)
    await db.commit()


async def _process_convert_task(task_id: int):
    """
    处理媒体转换任务的核心逻辑。

    1. 从 DB 读取任务参数
    2. 构建 FFmpeg 命令
    3. 执行 FFmpeg 并监控进度
    4. 创建输出文件记录
    5. 更新任务状态
    """
    trace_id = uuid.uuid4().hex[:16]
    _log_structured(
        event="task_started",
        task_id=task_id,
        trace_id=trace_id,
        span_id="span_init",
        extra={"func": "_process_convert_task"},
    )
    session_factory = _get_session_factory()
    async with session_factory() as db:
        try:
            # 1. 读取任务
            span_id = "span_read_task"
            _log_structured(
                event="reading_task", task_id=task_id, trace_id=trace_id,
                span_id=span_id, extra={"func": "_process_convert_task"},
            )
            result = await db.execute(select(MediaTask).where(MediaTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            user_id = task.user_id
            options = task.options_json
            tool_code = task.tool_name
            target_format = options.get("target_format", "mp4")

            # 更新为 processing
            span_id = "span_processing"
            _log_structured(
                event="task_processing_start", task_id=task_id, trace_id=trace_id,
                span_id=span_id, user_id=user_id,
                extra={"tool_code": tool_code, "target_format": target_format},
            )
            await _update_task_status(
                db, task_id, "processing", progress=5,
                trace_id=trace_id, span_id=span_id,
            )

            # 2. 读取输入文件
            span_id = "span_read_input"
            _log_structured(
                event="reading_input_file", task_id=task_id, trace_id=trace_id,
                span_id=span_id, user_id=user_id,
            )
            input_ids = json.loads(task.input_file_ids) if isinstance(task.input_file_ids, str) else task.input_file_ids
            if not input_ids:
                raise ValueError("input_file_ids 为空")

            input_file_id = input_ids[0]
            result = await db.execute(
                select(MediaFile).where(
                    MediaFile.id.in_(input_ids),
                    MediaFile.user_id == user_id,
                    MediaFile.deleted_at.is_(None),
                )
            )
            input_files = {item.id: item for item in result.scalars().all()}
            if len(input_files) != len(input_ids):
                raise FileNotFoundError("输入文件不存在")
            input_file = input_files[input_file_id]
            if any(not os.path.exists(input_files[file_id].storage_key) for file_id in input_ids):
                raise FileNotFoundError("输入文件已从磁盘移除")

            input_path = input_file.storage_key
            input_ext = input_file.source_format

            # 3. 构建输出路径
            output_dir = os.path.join(settings.MEDIA_UPLOAD_DIR, str(user_id), "output")
            os.makedirs(output_dir, exist_ok=True)

            output_name = f"{uuid.uuid4().hex}.{target_format}"
            output_path = os.path.join(output_dir, output_name)

            # 4. 构建 FFmpeg 命令。特殊工具只使用固定滤镜和参数，不接受原始表达式。
            if tool_code == "merge":
                manifest_path = os.path.join(output_dir, f"{uuid.uuid4().hex}.concat.txt")
                with open(manifest_path, "w", encoding="utf-8") as manifest:
                    for file_id in input_ids:
                        item = input_files[file_id]
                        escaped_path = Path(item.storage_key).resolve().as_posix().replace("'", "'\\''")
                        manifest.write(f"file '{escaped_path}'\n")
                temp_paths = [manifest_path]
                cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", manifest_path, "-c", "copy", "-y", output_path]

            elif tool_code == "gif":
                quality = options.get("quality", "medium")
                gif_quality = format_config.GIF_QUALITY[quality]
                width = int(options.get("width", 0) or gif_quality["width"])
                fps = int(options.get("frame_rate", 0) or gif_quality["fps"])
                start_time = float(options.get("start_time", 0) or 0)
                duration = float(options.get("duration", 0) or 0)
                vf = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer"
                cmd = ["ffmpeg", "-ss", str(start_time), "-t", str(duration), "-i", input_path, "-filter_complex", vf, "-loop", "0", "-y", output_path]
            elif tool_code == "watermark":
                watermark_file = input_files[input_ids[1]]
                position = options.get("position", "bottom-right")
                positions = {
                    "top-left": "10:10", "top-right": "main_w-overlay_w-10:10",
                    "bottom-left": "10:main_h-overlay_h-10", "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
                    "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
                }
                opacity = float(options.get("opacity", 1) or 1)
                watermark_width = int(options.get("watermark_width", 0) or 0)
                scale = f",scale={watermark_width}:-1" if watermark_width else ""
                filter_graph = f"[1:v]format=rgba,colorchannelmixer=aa={opacity}{scale}[wm];[0:v][wm]overlay={positions[position]}"
                cmd = ["ffmpeg", "-i", input_path, "-i", watermark_file.storage_key, "-filter_complex", filter_graph, "-c:a", "copy", "-c:v", "libx264", "-y", output_path]
            else:
                cmd = ["ffmpeg", "-i", input_path, "-y"]

                # 视频编码器
                video_codec = options.get("video_codec", "")
                if not video_codec:
                    video_codec = format_config.get_default_video_codec(target_format) or "libx264"
                if not format_config.is_audio_only_format(target_format):
                    cmd.extend(["-c:v", video_codec])

                # 音频编码器
                audio_codec = options.get("audio_codec", "")
                if not audio_codec:
                    audio_codec = format_config.get_default_audio_codec(target_format) or "aac"
                cmd.extend(["-c:a", audio_codec])

                resolution = options.get("resolution", "")
                if resolution:
                    if "x" in resolution:
                        cmd.extend(["-s", resolution])
                    elif resolution in format_config.RESOLUTION_PRESETS:
                        cmd.extend(["-vf", f"scale={format_config.RESOLUTION_PRESETS[resolution]}:-2"])
                frame_rate = options.get("frame_rate", 0)
                if frame_rate and frame_rate > 0:
                    cmd.extend(["-r", str(frame_rate)])
                sample_rate = options.get("sample_rate", 0)
                if sample_rate and sample_rate > 0:
                    cmd.extend(["-ar", str(sample_rate)])
                channels = options.get("channels", 0)
                if channels and channels > 0:
                    cmd.extend(["-ac", str(channels)])
                start_time = options.get("start_time", 0)
                duration = options.get("duration", 0)
                if start_time and start_time > 0:
                    cmd.extend(["-ss", str(start_time)])
                if duration and duration > 0:
                    cmd.extend(["-t", str(duration)])
                quality = options.get("quality", "medium")
                if quality in format_config.COMPRESSION_QUALITY:
                    quality_cfg = format_config.COMPRESSION_QUALITY[quality]
                    if quality_cfg["crf"] is not None:
                        cmd.extend(["-crf", str(quality_cfg["crf"])])
                    if quality_cfg["preset"]:
                        cmd.extend(["-preset", quality_cfg["preset"]])
                for option, flag in (("video_bitrate", "-b:v"), ("audio_bitrate", "-b:a")):
                    if options.get(option):
                        cmd.extend([flag, options[option]])
                if tool_code == "extract_audio":
                    cmd.extend(["-vn"])
                cmd.append(output_path)

            logger.info(
                "FFmpeg command prepared: task_id=%s tool=%s target_format=%s arg_count=%s",
                task_id,
                tool_code,
                target_format,
                len(cmd),
            )
            span_id = "span_ffmpeg_start"
            _log_structured(
                event="ffmpeg_executing", task_id=task_id, trace_id=trace_id,
                span_id=span_id, user_id=user_id,
                extra={"tool_code": tool_code, "target_format": target_format},
            )
            await _update_task_status(
                db, task_id, "processing", progress=10,
                trace_id=trace_id, span_id=span_id,
            )

            # 5. 执行 FFmpeg
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 读取 stderr 获取进度信息
            stderr_lines = []
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                stderr_lines.append(decoded)
                # 解析 time= 进度
                if "time=" in decoded:
                    try:
                        # 从 FFmpeg 输出解析 time=HH:MM:SS.xx
                        time_part = decoded.split("time=")[1].split()[0]
                        h, m, s = time_part.split(":")
                        seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        # 从输入文件获取总时长
                        total_dur = (input_file.duration_ms or 30000) / 1000
                        if total_dur > 0:
                            pct = min(95, int(10 + (seconds / total_dur) * 85))
                            await _update_task_status(
                                db, task_id, "processing", progress=pct,
                                trace_id=trace_id, span_id="span_ffmpeg_progress",
                            )
                    except (ValueError, IndexError):
                        pass

            await proc.wait()

            if await _is_task_cancelled(db, task_id):
                if os.path.exists(output_path):
                    os.remove(output_path)
                return

            if proc.returncode != 0:
                error_output = "\n".join(stderr_lines[-20:])
                raise RuntimeError(f"FFmpeg 失败 (code={proc.returncode}): {error_output[:500]}")

# 6. 检查输出文件
            if not os.path.exists(output_path):
                raise RuntimeError("FFmpeg 未生成输出文件")

            output_size = os.path.getsize(output_path)
            if output_size == 0:
                os.remove(output_path)
                raise RuntimeError("输出文件为空")

            span_id = "span_output"
            _log_structured(
                event="creating_output_record", task_id=task_id, trace_id=trace_id,
                span_id=span_id, user_id=user_id,
                extra={"output_size": output_size, "target_format": target_format},
            )
            await _update_task_status(
                db, task_id, "processing", progress=95,
                trace_id=trace_id, span_id=span_id,
            )

            # 7. 创建输出文件记录
            output_file = MediaFile(
                user_id=user_id,
                storage_key=output_path,
                original_name=f"output_{uuid.uuid4().hex[:8]}.{target_format}",
                media_type=format_config.get_media_kind(target_format),
                source_format=target_format,
                size_bytes=output_size,
                duration_ms=None,
                metadata_json={"source_task_id": task_id, "tool_code": tool_code},
                expires_at=datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1),
            )
            db.add(output_file)
            await db.commit()
            await db.refresh(output_file)

            # 8. 更新任务为 completed
            span_id = "span_completed"
            _log_structured(
                event="task_completed", task_id=task_id, trace_id=trace_id,
                span_id=span_id, user_id=user_id,
                extra={"output_file_id": output_file.id, "output_size": output_size},
)
            await _update_task_status(
                db, task_id, "completed",
                progress=100, output_file_id=output_file.id,
                trace_id=trace_id, span_id=span_id,
            )
            logger.info("Media task completed: task_id=%s output_size=%s", task_id, output_size)

        except asyncio.CancelledError:
            # 任务被取消，清理半成品
            logger.warning(f"Task {task_id} cancelled")
            if "output_path" in locals() and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            await _update_task_status(
                db, task_id, "cancelled", error_code="TASK_CANCELLED",
                trace_id=trace_id, span_id="span_cancelled",
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            # 清理临时输出
            if "temp_paths" in locals():
                for temp_path in temp_paths:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
            if "output_path" in locals() and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            await _update_task_status(
                db, task_id, "failed",
                error_code="FFMPEG_ERROR",
                error_message=str(e)[:500],
                trace_id=trace_id, span_id="span_failed",
            )


# ============================================================
# Celery 任务定义
# ============================================================


@celery_app.task(bind=True, name="media.process_media", max_retries=3, default_retry_delay=10)
def process_media_task(self, task_id: int):
    """
    媒体处理任务（for 媒体队列）。

    由 TASK API 调用，通过 Celery 路由到 media_tasks 队列。
"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_convert_task(task_id))
    except Exception as e:
        logger.error(f"Media task {task_id} unhandled error: {e}", exc_info=True)
        raise
    finally:
        loop.close()
        try:
            loop.run_until_complete(_dispose_engine())
        except Exception:
            pass


@celery_app.task(bind=True, name="media.health_check", max_retries=1)
def media_health_check(self):
    """
    媒体服务健康检查（T012）。

    检查：
    - 是否有长时间卡在 processing 的任务（> 15 分钟）
    - 是否有大量失败任务需要关注
    输出告警日志，供日志聚合系统触发告警。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_check_stuck_tasks())
    except Exception as e:
        logger.error(f"Media health check failed: {e}", exc_info=True)
    finally:
        loop.close()


async def _check_stuck_tasks():
    """检查卡住的任务并输出告警"""
    session_factory = _get_session_factory()
    async with session_factory() as db:
        try:
            # 1. 检查卡在 processing 超过 15 分钟的任务
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
            result = await db.execute(
                select(MediaTask).where(
                    MediaTask.status == "processing",
                    MediaTask.started_at < cutoff,
                )
            )
            stuck_tasks = result.scalars().all()
            for task in stuck_tasks:
                log_media_alert(
                    "media_queue_depth",
                    severity="warning",
                    task_id=task.id,
                    user_id=task.user_id,
                    tool_name=task.tool_name,
                    extra={"started_at": task.started_at.isoformat() if task.started_at else None},
                )

            # 2. 检查最近 1 小时内失败超过 3 次的任务
            hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            result = await db.execute(
                select(MediaTask).where(
                    MediaTask.status == "failed",
                    MediaTask.finished_at > hour_ago,
                )
            )
            failed_tasks = result.scalars().all()
            if len(failed_tasks) > 3:
                log_media_alert("media_task_success_rate", severity="high", extra={"failed_last_hour": len(failed_tasks)})
            log_media_metric("media_queue_depth", len(stuck_tasks), {"status": "processing_over_15m"})
            log_media_metric("media_worker_failure_total", len(failed_tasks), {"window": "1h"})

            logger.info(
                "Media health check: stuck=%d, recent_failures=%d",
                len(stuck_tasks), len(failed_tasks),
            )

        except Exception as e:
            logger.error(f"Media health check error: {e}", exc_info=True)
