from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.user import User
from app.models.interview import Interview
from app.models.experience import Experience
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


@router.get("/pageview-trend")
async def pageview_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """每日浏览量趋势（PV）"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            cast(PageView.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(PageView.created_at >= start_date)
        .group_by(cast(PageView.created_at, Date))
        .order_by(cast(PageView.created_at, Date))
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


@router.get("/geo-distribution")
async def geo_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """用户地理分布：国家 + 省份 Top N"""
    # 国家分布 Top 10
    country_result = await db.execute(
        select(PageView.country, func.count().label("count"))
        .where(PageView.country.isnot(None))
        .group_by(PageView.country)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_countries = [
        {"name": row.country, "count": row.count}
        for row in country_result.all() if row.country
    ]

    # 省份分布 Top 10
    province_result = await db.execute(
        select(PageView.province, func.count().label("count"))
        .where(PageView.province.isnot(None))
        .group_by(PageView.province)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_provinces = [
        {"name": row.province, "count": row.count}
        for row in province_result.all() if row.province
    ]

    # 独立 IP 数（已记录 IP 的去重统计）
    unique_ips = await db.scalar(
        select(func.count(func.distinct(PageView.ip)))
        .where(PageView.ip.isnot(None))
    ) or 0

    return ApiResponse.success(data={
        "top_countries": top_countries,
        "top_provinces": top_provinces,
        "unique_ips": unique_ips,
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


@router.get("/pv-trend")
async def pv_trend(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """每日页面浏览量趋势"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            cast(PageView.created_at, Date).label("date"),
            func.count().label("count"),
        )
        .where(PageView.created_at >= start_date)
        .group_by(cast(PageView.created_at, Date))
        .order_by(cast(PageView.created_at, Date))
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


@router.get("/geo-distribution")
async def geo_distribution(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """访客地域分布（按 IP 聚合 Top 15，因 country/province 暂未填充）"""
    # 按 IP 聚合访问次数
    result = await db.execute(
        select(
            PageView.ip,
            func.count().label("count"),
        )
        .where(PageView.ip.isnot(None), PageView.ip != "")
        .group_by(PageView.ip)
        .order_by(func.count().desc())
        .limit(15)
    )
    rows = result.all()
    regions = [
        {"ip": row.ip, "visits": row.count}
        for row in rows
    ]

    # 按 province 聚合（如果已填充）
    province_result = await db.execute(
        select(
            func.coalesce(PageView.province, "未知").label("province"),
            func.count().label("count"),
        )
        .group_by("province")
        .order_by(func.count().desc())
        .limit(15)
    )
    province_rows = province_result.all()
    provinces = [
        {"name": row.province, "visits": row.count}
        for row in province_rows
    ]

    return ApiResponse.success(data={
        "regions": regions,
        "provinces": provinces,
        "total_unique_ips": len(regions),
    })
