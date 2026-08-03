"""
媒体工具 Repository 层（T004）

封装媒体文件、任务和事件的数据库查询，所有查询自动限制 user_id。
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_tool import MediaFile, MediaTask, MediaEvent
from app.exceptions.http_exceptions import NotFoundError, APIException

logger = logging.getLogger(__name__)


class MediaFileRepository:
    """媒体文件 Repository"""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        storage_key: str,
        original_name: str,
        media_type: str,
        source_format: str,
        size_bytes: int,
        duration_ms: Optional[int] = None,
        metadata_json: Optional[Dict] = None,
        expires_at: Optional[datetime] = None,
    ) -> MediaFile:
        """创建媒体文件记录"""
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        record = MediaFile(
            user_id=user_id,
            storage_key=storage_key,
            original_name=original_name,
            media_type=media_type,
            source_format=source_format,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
            metadata_json=metadata_json or {},
            expires_at=expires_at,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_by_id(db: AsyncSession, file_id: int, user_id: int) -> Optional[MediaFile]:
        """按 ID 查询（带用户权限）"""
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.id == file_id,
                MediaFile.user_id == user_id,
                MediaFile.media_type != "deleted",
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id_admin(db: AsyncSession, file_id: int) -> Optional[MediaFile]:
        """按 ID 查询（管理员，无用户限制）"""
        result = await db.execute(
            select(MediaFile).where(MediaFile.id == file_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
        media_type: Optional[str] = None,
    ) -> Dict:
        """查询用户的文件列表"""
        query = select(MediaFile).where(
            MediaFile.user_id == user_id,
            MediaFile.media_type != "deleted",
        )
        if media_type:
            query = query.where(MediaFile.media_type == media_type)

        # 总数
        count_q = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_q)

        # 分页
        result = await db.execute(
            query.order_by(MediaFile.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": f.id,
                    "original_name": f.original_name,
                    "media_type": f.media_type,
                    "source_format": f.source_format,
                    "size_bytes": f.size_bytes,
                    "duration_ms": f.duration_ms,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "expires_at": f.expires_at.isoformat() if f.expires_at else None,
                }
                for f in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "has_more": (page * size) < total,
        }

    @staticmethod
    async def soft_delete(db: AsyncSession, file_id: int, user_id: int) -> bool:
        """软删除文件（仅当未被任务引用时）"""
        # 检查是否被任务引用
        result = await db.execute(
            select(func.count(MediaTask.id)).where(
                MediaTask.output_file_id == file_id,
                MediaTask.status.in_(["queued", "processing", "completed"]),
            )
)
        ref_count = result.scalar()
        if ref_count > 0:
            raise APIException(
                code=10406,
                message="文件正在被任务引用，无法删除",
                status_code=409,
            )

        # 软删除：设置 media_type = "deleted"
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.id == file_id,
                MediaFile.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundError(message="文件不存在")

        record.media_type = "deleted"
        await db.commit()
        return True

    @staticmethod
    async def get_expired_files(db: AsyncSession) -> List[MediaFile]:
        """查询过期文件（用于清理任务）"""
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.expires_at < datetime.now(timezone.utc),
                MediaFile.media_type != "deleted",
            )
        )
        return result.scalars().all()


class MediaTaskRepository:
    """媒体任务 Repository"""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        tool_name: str,
        input_file_ids: List[int],
        options_json: Optional[Dict] = None,
    ) -> MediaTask:
        """创建任务记录"""
        record = MediaTask(
            user_id=user_id,
            tool_name=tool_name,
            status="pending",
            input_file_ids=json.dumps(input_file_ids) if input_file_ids else "[]",
            options_json=options_json or {},
            progress=0,
            retry_count=0,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: int, user_id: int) -> Optional[MediaTask]:
        """按 ID 查询（带用户权限）"""
        result = await db.execute(
            select(MediaTask).where(
                MediaTask.id == task_id,
                MediaTask.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
        status: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict:
        """查询用户的任务历史"""
        query = select(MediaTask).where(MediaTask.user_id == user_id)
        if status:
            query = query.where(MediaTask.status == status)
        if tool_name:
            query = query.where(MediaTask.tool_name == tool_name)

        count_q = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_q)

        result = await db.execute(
            query.order_by(MediaTask.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": t.id,
                    "tool_name": t.tool_name,
                    "status": t.status,
                    "progress": t.progress,
                    "error_code": t.error_code,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "finished_at": t.finished_at.isoformat() if t.finished_at else None,
                }
                for t in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "has_more": (page * size) < total,
        }

    @staticmethod
    async def check_duplicate(
        db: AsyncSession,
        user_id: int,
        tool_name: str,
        input_file_ids: List[int],
        options_json: Dict,
    ) -> bool:
        """检查是否存在相同的正在执行的任务"""
        result = await db.execute(
            select(MediaTask).where(
                MediaTask.user_id == user_id,
                MediaTask.tool_name == tool_name,
                MediaTask.status.in_(["pending", "processing"]),
                MediaTask.input_file_ids == json.dumps(input_file_ids),
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def update_status(
        db: AsyncSession,
        task_id: int,
        status: str,
        progress: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        output_file_id: Optional[int] = None,
        celery_task_id: Optional[str] = None,
    ):
        """更新任务状态"""
        values = {}
        if status:
            values["status"] = status
        if progress is not None:
            values["progress"] = progress
        if error_code:
            values["error_code"] = error_code
        if error_message:
            values["error_message"] = error_message
        if output_file_id is not None:
            values["output_file_id"] = output_file_id
        if celery_task_id:
            values["celery_task_id"] = celery_task_id

        if status == "processing":
            values["started_at"] = datetime.now(timezone.utc)
        if status in ("completed", "failed", "cancelled"):
            values["finished_at"] = datetime.now(timezone.utc)

        if values:
            stmt = update(MediaTask).where(MediaTask.id == task_id).values(**values)
            await db.execute(stmt)
            await db.commit()

    @staticmethod
    async def cancel_task(db: AsyncSession, task_id: int, user_id: int) -> bool:
        """取消任务"""
        result = await db.execute(
            select(MediaTask).where(
                MediaTask.id == task_id,
                MediaTask.user_id == user_id,
                MediaTask.status.in_(["pending", "processing"]),
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(message="无可取消的任务")

        task.status = "cancelled"
        task.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    @staticmethod
    async def retry_task(db: AsyncSession, task_id: int, user_id: int) -> MediaTask:
        """重试失败任务"""
        result = await db.execute(
            select(MediaTask).where(
                MediaTask.id == task_id,
                MediaTask.user_id == user_id,
                MediaTask.status == "failed",
            )
        )
        task = result.scalar_one_or_none()
        if not task:
            raise NotFoundError(message="无可重试的任务")

        if task.retry_count >= 3:
            raise NotFoundError(message="超过最大重试次数")

        task.status = "pending"
        task.progress = 0
        task.error_code = None
        task.finished_at = None
        task.retry_count = (task.retry_count or 0) + 1
        await db.commit()
        return task


class MediaEventRepository:
    """媒体事件 Repository"""

    @staticmethod
    async def create(
        db: AsyncSession,
        task_id: int,
        user_id: int,
        event_name: str,
        payload_json: Optional[Dict] = None,
    ) -> MediaEvent:
        """创建事件记录"""
        record = MediaEvent(
            task_id=task_id,
            user_id=user_id,
            event_name=event_name,
            payload_json=payload_json or {},
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_by_task(db: AsyncSession, task_id: int) -> List[MediaEvent]:
        """查询任务的事件列表"""
        result = await db.execute(
            select(MediaEvent)
            .where(MediaEvent.task_id == task_id)
            .order_by(MediaEvent.created_at.asc())
        )
        return result.scalars().all()