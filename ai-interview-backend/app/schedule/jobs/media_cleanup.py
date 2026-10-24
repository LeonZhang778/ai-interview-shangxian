"""
媒体存储清理定时任务（窗口 W1：P0 存储治理）

由 Celery Beat 每天 03:40 触发，回收 uploads/media 磁盘空间：

1. 过期文件：``expires_at < now`` 且 ``deleted_at IS NULL`` → 删磁盘 + 写
   ``deleted_at``（保留审计记录，不物理删行）。
2. 软删超期：``deleted_at < now - 7d`` → 确认磁盘文件已不存在（存在则先删，
   删不掉就跳过本轮，防止「记录没了、文件还在」）→ 物理删除 DB 记录。
3. 孤儿任务输出：产出任务已被删除、文件仍有效但已过期 → 按第 1 条处理。
   它本就是第 1 条的子集，先跑以便在日志里单独看到数量；顺序不影响覆盖范围。

安全阀：
- 单轮最多处理 ``MEDIA_CLEANUP_BATCH``（默认 500）条，超出留到下轮，避免长事务。
- ``expires_at IS NULL`` 一律不动；只删明确早于当前时间的记录。
- 单个文件删除失败只记 warning 继续，不回滚整批。
- ``MEDIA_CLEANUP_ENABLED=false`` 时任务直接返回（紧急停用开关）。
- ``MEDIA_CLEANUP_DRY_RUN=true`` 时只统计并输出日志、不真删（上线前观察用）。

开关与批量大小从环境变量读取：本窗口不改 app/core/config.py（窗口独占文件约束）。
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.core.async_runner import run_async
from app.core.celery_app import celery_app
from app.db.session import async_session
from app.models.media_tool import MediaFile, MediaTask
from app.services.media.repository import MediaFileRepository

logger = logging.getLogger(__name__)

DEFAULT_BATCH = 500
SOFT_DELETE_RETENTION_DAYS = 7


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _batch_size() -> int:
    raw = os.environ.get("MEDIA_CLEANUP_BATCH")
    if raw is None:
        return DEFAULT_BATCH
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_BATCH
    return value if value > 0 else DEFAULT_BATCH


def should_purge_expired(
    expires_at: Optional[datetime],
    deleted_at: Optional[datetime],
    now: datetime,
) -> bool:
    """过期清理筛选（纯函数）：只动「未软删且 expires_at 明确早于 now」的记录。

    expires_at 为空或未过期、已软删的一律不动（软删的交给下一阶段）。
    """
    if deleted_at is not None:
        return False
    if expires_at is None:
        return False
    return expires_at < now


def should_hard_delete(
    deleted_at: Optional[datetime],
    now: datetime,
    retention_days: int = SOFT_DELETE_RETENTION_DAYS,
) -> bool:
    """软删超期筛选（纯函数）：deleted_at 为空或未满保留期都不动。"""
    if deleted_at is None:
        return False
    return deleted_at < now - timedelta(days=retention_days)


async def _purge_expired_pass(
    db,
    now: datetime,
    budget: int,
    *,
    orphan_only: bool,
    dry_run: bool,
) -> tuple:
    """处理「已过期且未软删」的文件，返回 (剩余预算, 处理条数, 释放字节)。"""
    if budget <= 0:
        return budget, 0, 0

    query = (
        select(MediaFile)
        .where(
            MediaFile.deleted_at.is_(None),
            MediaFile.expires_at.isnot(None),
            MediaFile.expires_at < now,
        )
        .order_by(MediaFile.expires_at.asc())
        .limit(budget)
    )
    if orphan_only:
        query = query.where(
            ~select(MediaTask.id).where(MediaTask.output_file_id == MediaFile.id).exists()
        )
    rows = (await db.execute(query)).scalars().all()

    purged = 0
    released = 0
    for record in rows:
        if not should_purge_expired(record.expires_at, record.deleted_at, now):
            continue
        if dry_run:
            purged += 1
            released += record.size_bytes or 0
            continue
        try:
            freed = await MediaFileRepository.purge_file(db, record.id)
        except Exception as e:  # 单文件失败不中断整批
            logger.warning("media.cleanup 清理过期文件失败 file_id=%s: %s", record.id, e)
            continue
        purged += 1
        released += freed

    label = "孤儿任务输出" if orphan_only else "过期文件"
    logger.info(
        "media.cleanup %s：%s %d 条，释放 %d 字节（dry_run=%s）",
        label,
        "将清理" if dry_run else "清理",
        purged,
        released,
        dry_run,
    )
    return budget - len(rows), purged, released


async def _hard_delete_pass(db, now: datetime, budget: int, *, dry_run: bool) -> int:
    """软删超期：确认磁盘已无文件后物理删除 DB 记录，返回处理条数。"""
    if budget <= 0:
        logger.warning("media.cleanup 本轮批量预算已用尽，软删超期清理推迟到下轮")
        return 0

    cutoff = now - timedelta(days=SOFT_DELETE_RETENTION_DAYS)
    rows = (
        await db.execute(
            select(MediaFile)
            .where(MediaFile.deleted_at.isnot(None), MediaFile.deleted_at < cutoff)
            .order_by(MediaFile.deleted_at.asc())
            .limit(budget)
        )
    ).scalars().all()

    removed = 0
    for record in rows:
        if not should_hard_delete(record.deleted_at, now):
            continue
        path = record.storage_key
        if path and os.path.isfile(path):
            if dry_run:
                removed += 1
                continue
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(
                    "media.cleanup 软删超期：残留磁盘文件删除失败 file_id=%s，跳过本轮: %s",
                    record.id,
                    e,
                )
                continue
        if dry_run:
            removed += 1
            continue
        await db.delete(record)
        await db.commit()
        removed += 1

    logger.info(
        "media.cleanup 软删超期：%s %d 条 DB 记录（保留期 %d 天，dry_run=%s）",
        "将物理删除" if dry_run else "物理删除",
        removed,
        SOFT_DELETE_RETENTION_DAYS,
        dry_run,
    )
    return removed


async def _cleanup_round() -> dict:
    now = datetime.now(timezone.utc)
    budget = _batch_size()
    dry_run = _env_flag("MEDIA_CLEANUP_DRY_RUN", False)

    stats = {
        "orphan_outputs": 0,
        "expired_files": 0,
        "released_bytes": 0,
        "hard_deleted": 0,
        "dry_run": dry_run,
    }

    async with async_session() as db:
        # 1) 孤儿任务输出先处理（过期未删的子集），便于单独统计
        budget, purged, released = await _purge_expired_pass(
            db, now, budget, orphan_only=True, dry_run=dry_run
        )
        stats["orphan_outputs"] = purged
        stats["released_bytes"] += released

        # 2) 其余过期文件
        budget, purged, released = await _purge_expired_pass(
            db, now, budget, orphan_only=False, dry_run=dry_run
        )
        stats["expired_files"] = purged
        stats["released_bytes"] += released

        # 3) 软删超期 → 物理删除记录
        stats["hard_deleted"] = await _hard_delete_pass(db, now, budget, dry_run=dry_run)

    logger.info(
        "media.cleanup 本轮完成：孤儿 %d / 过期 %d / 物理删 %d，释放 %d 字节（dry_run=%s）",
        stats["orphan_outputs"],
        stats["expired_files"],
        stats["hard_deleted"],
        stats["released_bytes"],
        dry_run,
    )
    return stats


@celery_app.task(name="media.cleanup_expired")
def cleanup_expired():
    """过期媒体文件清理（beat 每天 03:40 触发，media_tasks 队列）。

    同步入口统一走 run_async（进程常驻事件循环），避免 DB 单例连接跨循环失效。
    """
    if not _env_flag("MEDIA_CLEANUP_ENABLED", True):
        logger.info("media.cleanup_expired：MEDIA_CLEANUP_ENABLED=false，跳过本轮")
        return {"skipped": True}
    return run_async(_cleanup_round())
