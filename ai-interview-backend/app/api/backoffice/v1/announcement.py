from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.announcement import Announcement
from app.schemas.response import ApiResponse
from app.exceptions.http_exceptions import NotFoundError
from app.common.audit import log_audit

router = APIRouter()


@router.get("")
async def list_announcements(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    announcement_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取公告列表"""
    query = select(Announcement).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
    count_query = select(func.count()).select_from(Announcement)

    if announcement_type:
        query = query.where(Announcement.announcement_type == announcement_type)
        count_query = count_query.where(Announcement.announcement_type == announcement_type)
    if is_active is not None:
        query = query.where(Announcement.is_active == is_active)
        count_query = count_query.where(Announcement.is_active == is_active)

    total = await db.scalar(count_query)
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    announcements = result.scalars().all()

    items = [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "type": a.announcement_type,
            "level": a.level or "P1",
            "is_pinned": a.is_pinned,
            "is_active": a.is_active,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "expired_at": a.expired_at.isoformat() if a.expired_at else None,
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
        }
        for a in announcements
    ]

    return ApiResponse.success(data={"items": items, "total": total, "page": page, "per_page": per_page})


@router.post("")
async def create_announcement(
    title: str,
    content: str,
    announcement_type: str = "info",
    level: str = "P1",
    is_pinned: bool = False,
    published_at: Optional[str] = None,
    expired_at: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """创建公告"""
    announcement = Announcement(
        title=title,
        content=content,
        announcement_type=announcement_type,
        level=level,
        is_pinned=is_pinned,
        is_active=True,
        published_at=datetime.fromisoformat(published_at) if published_at else datetime.now(timezone.utc),
        expired_at=datetime.fromisoformat(expired_at) if expired_at else None,
        created_by=current_admin.id,
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    await log_audit(db, current_admin.id, "create", "announcement", announcement.id,
                    f"创建公告: {title}")

    return ApiResponse.success(data={
        "id": announcement.id,
        "title": announcement.title,
        "is_active": announcement.is_active,
    })


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    announcement_type: Optional[str] = None,
    level: Optional[str] = None,
    is_pinned: Optional[bool] = None,
    published_at: Optional[str] = None,
    expired_at: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """编辑公告"""
    announcement = await db.get(Announcement, announcement_id)
    if not announcement:
        return ApiResponse.failed(message="公告不存在", body_code=404, http_code=404)

    if title is not None:
        announcement.title = title
    if content is not None:
        announcement.content = content
    if announcement_type is not None:
        announcement.announcement_type = announcement_type
    if level is not None:
        announcement.level = level
    if is_pinned is not None:
        announcement.is_pinned = is_pinned
    if published_at is not None:
        announcement.published_at = datetime.fromisoformat(published_at) if published_at else None
    if expired_at is not None:
        announcement.expired_at = datetime.fromisoformat(expired_at) if expired_at else None

    await db.commit()

    await log_audit(db, current_admin.id, "update", "announcement", announcement_id,
                    f"编辑公告: {announcement.title}")

    return ApiResponse.success(data={"id": announcement.id})


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除公告"""
    announcement = await db.get(Announcement, announcement_id)
    if not announcement:
        return ApiResponse.failed(message="公告不存在", body_code=404, http_code=404)

    title = announcement.title
    await db.delete(announcement)
    await db.commit()

    await log_audit(db, current_admin.id, "delete", "announcement", announcement_id,
                    f"删除公告: {title}")

    return ApiResponse.success(message="删除成功")


@router.put("/{announcement_id}/pin")
async def toggle_pin(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """切换置顶状态"""
    announcement = await db.get(Announcement, announcement_id)
    if not announcement:
        return ApiResponse.failed(message="公告不存在", body_code=404, http_code=404)

    announcement.is_pinned = not announcement.is_pinned
    await db.commit()

    await log_audit(db, current_admin.id, "update", "announcement", announcement_id,
                    f"{'置顶' if announcement.is_pinned else '取消置顶'}公告: {announcement.title}")

    return ApiResponse.success(data={"is_pinned": announcement.is_pinned})


@router.put("/{announcement_id}/status")
async def toggle_status(
    announcement_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """切换上线/下线状态"""
    announcement = await db.get(Announcement, announcement_id)
    if not announcement:
        return ApiResponse.failed(message="公告不存在", body_code=404, http_code=404)

    announcement.is_active = is_active
    await db.commit()

    await log_audit(db, current_admin.id, "update", "announcement", announcement_id,
                    f"{'上线' if is_active else '下线'}公告: {announcement.title}")

    return ApiResponse.success(data={"is_active": announcement.is_active})
