import logging
from typing import Dict, Optional
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        notification_type: str = "system",
        related_id: Optional[int] = None,
        related_type: Optional[str] = None,
        commit: bool = True,
    ) -> None:
        """创建通知"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                content=content,
                notification_type=notification_type,
                related_id=related_id,
                related_type=related_type,
            )
            db.add(notification)
            if commit:
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to create notification: {e}")
            await db.rollback()

    @staticmethod
    async def get_notifications(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        """获取通知列表"""
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        count_query = select(func.count()).select_from(
            select(Notification).where(Notification.user_id == user_id).subquery()
        )
        total = await db.scalar(count_query)

        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        notifications = result.scalars().all()

        items = [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "type": n.notification_type,
                "related_id": n.related_id,
                "related_type": n.related_type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        """获取未读通知数量"""
        count = await db.scalar(
            select(func.count()).select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
        )
        return count or 0

    @staticmethod
    async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> None:
        """标记单条通知已读"""
        notification = await db.get(Notification, notification_id)
        if notification and notification.user_id == user_id and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(UTC)
            await db.commit()

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        """标记所有通知已读"""
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        await db.commit()
        return result.rowcount

    @staticmethod
    async def delete_notification(db: AsyncSession, user_id: int, notification_id: int) -> None:
        """删除通知"""
        notification = await db.get(Notification, notification_id)
        if notification and notification.user_id == user_id:
            await db.delete(notification)
            await db.commit()


notification_service = NotificationService()
