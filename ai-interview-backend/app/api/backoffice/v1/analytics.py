from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.user import User
from app.models.interview import Interview
from app.models.experience import Experience, UserLike, UserCollection
from app.models.image_task import ImageTask
from app.models.page_view import PageView
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    total_interviews = await db.scalar(select(func.count()).select_from(Interview)) or 0
    total_experiences = await db.scalar(select(func.count()).select_from(Experience)) or 0
    total_images = await db.scalar(select(func.count()).select_from(ImageTask)) or 0

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_new_users = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today)
    ) or 0
    today_interviews = await db.scalar(
        select(func.count()).select_from(Interview).where(Interview.created_at >= today)
    ) or 0

    completed = await db.scalar(
        select(func.count()).select_from(Interview).where(Interview.status == "completed")
    ) or 0
    completion_rate = round(completed / total_interviews, 2) if total_interviews > 0 else 0

    avg_score_result = await db.scalar(
        select(func.avg(Interview.overall_score)).where(Interview.overall_score.isnot(None))
    )
    average_score = round(float(avg_score_result), 1) if avg_score_result else 0

    return ApiResponse.success(data={
        "total_users": total_users,
        "total_interviews": total_interviews,
        "total_experiences": total_experiences,
        "total_images": total_images,
        "today_new_users": today_new_users,
        "today_interviews": today_interviews,
        "completion_rate": completion_rate,
        "average_score": average_score,
    })


@router.get("/user-trend")
async def user_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            cast(User.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(User.created_at >= start_date)
        .group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
    )
    rows = result.all()

    date_count = {str(row.date): row.count for row in rows}
    labels = []
    data = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(d)
        data.append(date_count.get(d, 0))

    return ApiResponse.success(data={"labels": labels, "data": data})


@router.get("/interview-trend")
async def interview_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            cast(Interview.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(Interview.created_at >= start_date)
        .group_by(cast(Interview.created_at, Date))
        .order_by(cast(Interview.created_at, Date))
    )
    rows = result.all()

    date_count = {str(row.date): row.count for row in rows}
    labels = []
    data = []
    for i in range(days):
        d = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(d)
        data.append(date_count.get(d, 0))

    return ApiResponse.success(data={"labels": labels, "data": data})


@router.get("/experience-ranking")
async def experience_ranking(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    # Top 10 by likes
    likes_result = await db.execute(
        select(Experience.id, Experience.title, func.count(UserLike.id).label("likes"))
        .outerjoin(UserLike, UserLike.experience_id == Experience.id)
        .group_by(Experience.id, Experience.title)
        .order_by(func.count(UserLike.id).desc())
        .limit(10)
    )
    top_likes = [
        {"id": row.id, "title": row.title, "count": row.likes}
        for row in likes_result.all()
    ]

    # Top 10 by collections
    collections_result = await db.execute(
        select(Experience.id, Experience.title, func.count(UserCollection.user_id).label("collections"))
        .outerjoin(UserCollection, UserCollection.experience_id == Experience.id)
        .group_by(Experience.id, Experience.title)
        .order_by(func.count(UserCollection.user_id).desc())
        .limit(10)
    )
    top_collections = [
        {"id": row.id, "title": row.title, "count": row.collections}
        for row in collections_result.all()
    ]

    return ApiResponse.success(data={
        "top_likes": top_likes,
        "top_collections": top_collections,
    })


@router.get("/active-users")
async def active_users(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # DAU/WAU 基于 last_active_at 统计（排除游客）
    dau = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.last_active_at >= today, User.is_guest == False)
    ) or 0

    wau = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.last_active_at >= week_ago, User.is_guest == False)
    ) or 0

    # 今日 PV/UV
    today_pv = await db.scalar(
        select(func.count()).select_from(PageView)
        .where(PageView.created_at >= today)
    ) or 0

    today_uv = await db.scalar(
        select(func.count(func.distinct(PageView.session_id)))
        .where(PageView.created_at >= today, PageView.session_id.isnot(None))
    ) or 0

    return ApiResponse.success(data={"dau": dau, "wau": wau, "today_pv": today_pv, "today_uv": today_uv})
