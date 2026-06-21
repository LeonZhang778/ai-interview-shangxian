from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.services.client.notification_service import notification_service
from app.schemas.response import ApiResponse
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取通知列表"""
    result = await notification_service.get_notifications(
        db=db, user_id=current_user.id, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取未读通知数量"""
    count = await notification_service.get_unread_count(db=db, user_id=current_user.id)
    return ApiResponse.success(data={"count": count})


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记通知已读"""
    await notification_service.mark_read(db=db, user_id=current_user.id, notification_id=notification_id)
    return ApiResponse.success(data=None)


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """标记所有通知已读"""
    count = await notification_service.mark_all_read(db=db, user_id=current_user.id)
    return ApiResponse.success(data={"marked": count})


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除通知"""
    await notification_service.delete_notification(db=db, user_id=current_user.id, notification_id=notification_id)
    return ApiResponse.success(data=None)
