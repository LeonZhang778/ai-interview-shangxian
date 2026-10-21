from typing import Optional

from app.core.async_runner import run_async
from app.core.celery_app import celery_app
from app.db.session import async_session
from app.services.client.notification_service import notification_service


@celery_app.task(name="notification.create")
def create_notification_task(
    user_id: int,
    title: str,
    content: Optional[str] = None,
    notification_type: str = "system",
    related_id: Optional[int] = None,
    related_type: Optional[str] = None,
):
    """异步创建非事务依赖通知。

    经 run_async 跑在进程常驻事件循环上，避免逐任务开关循环导致
    DB 单例连接池跨循环复用报错（同 resume_tasks 说明）。
    """
    return run_async(_create_notification(
        user_id=user_id,
        title=title,
        content=content,
        notification_type=notification_type,
        related_id=related_id,
        related_type=related_type,
    ))


async def _create_notification(
    user_id: int,
    title: str,
    content: Optional[str],
    notification_type: str,
    related_id: Optional[int],
    related_type: Optional[str],
):
    async with async_session() as db:
        await notification_service.create_notification(
            db=db,
            user_id=user_id,
            title=title,
            content=content,
            notification_type=notification_type,
            related_id=related_id,
            related_type=related_type,
            commit=True,
        )
    return {"user_id": user_id, "status": "created"}
