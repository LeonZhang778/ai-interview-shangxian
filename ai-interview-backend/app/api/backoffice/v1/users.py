from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.user import User
from app.models.resume import Resume
from app.models.interview import Interview
from app.models.token import Token
from app.schemas.response import ApiResponse
from app.common.audit import log_audit

router = APIRouter()


@router.get("")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    keyword: str = None,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取用户列表"""
    query = select(User).order_by(User.created_at.desc())
    count_query = select(func.count()).select_from(User)

    if keyword:
        query = query.where(
            (User.email.ilike(f"%{keyword}%")) |
            (User.first_name.ilike(f"%{keyword}%")) |
            (User.last_name.ilike(f"%{keyword}%"))
        )
        count_query = count_query.where(
            (User.email.ilike(f"%{keyword}%")) |
            (User.first_name.ilike(f"%{keyword}%")) |
            (User.last_name.ilike(f"%{keyword}%"))
        )

    total = await db.scalar(count_query)
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    items = [
        {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

    return ApiResponse.success(data={"items": items, "total": total, "page": page, "per_page": per_page})


@router.put("/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """启用/禁用用户"""
    user = await db.get(User, user_id)
    if not user:
        return ApiResponse.failed(message="用户不存在", body_code=404, http_code=404)

    user.is_active = not user.is_active
    await db.commit()

    action = "enable" if user.is_active else "disable"
    await log_audit(db, current_admin.id, action, "user", user_id,
                    f"{'启用' if user.is_active else '禁用'}用户: {user.email}")

    return ApiResponse.success(data={"is_active": user.is_active})


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取平台统计数据"""
    user_count = await db.scalar(select(func.count()).select_from(User))
    resume_count = await db.scalar(select(func.count()).select_from(Resume))
    interview_count = await db.scalar(select(func.count()).select_from(Interview))
    completed_count = await db.scalar(
        select(func.count()).select_from(Interview).where(Interview.status == "completed")
    )

    return ApiResponse.success(data={
        "user_count": user_count or 0,
        "resume_count": resume_count or 0,
        "interview_count": interview_count or 0,
        "completed_interview_count": completed_count or 0
    })


@router.delete("/guests/cleanup")
async def cleanup_guest_users(
    days: int = Query(30, ge=7, le=365, description="清理多少天未活跃的游客"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """清理长期未活跃的游客用户"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 统计待清理数量
    count = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.is_guest == True, User.last_active_at < cutoff)
    ) or 0

    if count == 0:
        return ApiResponse.success(data={"deleted": 0, "message": "没有需要清理的游客用户"})

    # 先删除关联的 token
    guest_ids = await db.execute(
        select(User.id).where(User.is_guest == True, User.last_active_at < cutoff)
    )
    ids = [row[0] for row in guest_ids.all()]
    if ids:
        await db.execute(delete(Token).where(Token.user_id.in_(ids)))
        await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()

    await log_audit(db, current_admin.id, "cleanup", "guest_users", None,
                    f"清理 {count} 个超过 {days} 天未活跃的游客用户")

    return ApiResponse.success(data={"deleted": count})
