from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.db.session import get_db
from app.models.announcement import Announcement
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("")
async def get_announcements(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取当前有效公告列表（无需登录）"""
    now = datetime.now(timezone.utc)
    query = (
        select(Announcement)
        .where(Announcement.is_active == True)
        .where(or_(Announcement.published_at.is_(None), Announcement.published_at <= now))
        .where(or_(Announcement.expired_at.is_(None), Announcement.expired_at > now))
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    announcements = result.scalars().all()

    items = [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "type": a.announcement_type,
            "is_pinned": a.is_pinned,
            "published_at": a.published_at.isoformat() if a.published_at else a.created_at.isoformat(),
        }
        for a in announcements
    ]

    return ApiResponse.success(data={"items": items, "total": total, "page": page, "per_page": size})


@router.get("/latest")
async def get_latest_announcement(
    db: AsyncSession = Depends(get_db)
):
    """获取最新一条公告（首页横幅用）"""
    now = datetime.now(timezone.utc)
    query = (
        select(Announcement)
        .where(Announcement.is_active == True)
        .where(or_(Announcement.published_at.is_(None), Announcement.published_at <= now))
        .where(or_(Announcement.expired_at.is_(None), Announcement.expired_at > now))
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    announcement = result.scalar_one_or_none()

    if not announcement:
        return ApiResponse.success(data=None)

    return ApiResponse.success(data={
        "id": announcement.id,
        "title": announcement.title,
        "content": announcement.content,
        "type": announcement.announcement_type,
        "is_pinned": announcement.is_pinned,
        "published_at": announcement.published_at.isoformat() if announcement.published_at else announcement.created_at.isoformat(),
    })


@router.get("/{announcement_id}")
async def get_announcement_detail(
    announcement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取公告详情"""
    now = datetime.now(timezone.utc)
    query = (
        select(Announcement)
        .where(Announcement.id == announcement_id)
        .where(Announcement.is_active == True)
        .where(or_(Announcement.published_at.is_(None), Announcement.published_at <= now))
        .where(or_(Announcement.expired_at.is_(None), Announcement.expired_at > now))
    )
    result = await db.execute(query)
    announcement = result.scalar_one_or_none()

    if not announcement:
        return ApiResponse.failed(message="公告不存在", body_code=404, http_code=404)

    return ApiResponse.success(data={
        "id": announcement.id,
        "title": announcement.title,
        "content": announcement.content,
        "type": announcement.announcement_type,
        "is_pinned": announcement.is_pinned,
        "published_at": announcement.published_at.isoformat() if announcement.published_at else announcement.created_at.isoformat(),
        "created_at": announcement.created_at.isoformat(),
    })
