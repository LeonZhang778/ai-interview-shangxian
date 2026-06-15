from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.services.client.experience_service import experience_service
from app.schemas.response import ApiResponse
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_experiences(
    company: Optional[str] = Query(None, description="公司筛选"),
    position: Optional[str] = Query(None, description="岗位筛选"),
    level: Optional[str] = Query(None, description="经验级别"),
    round: Optional[str] = Query(None, description="面试轮次"),
    sort: str = Query("latest", description="排序: latest/popular/collected"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取面经列表（无需登录）"""
    result = await experience_service.get_experiences(
        db=db,
        company=company,
        position=position,
        level=level,
        round_=round,
        sort=sort,
        page=page,
        size=size
    )
    return ApiResponse.success(data=result)


@router.get("/filters")
async def get_filter_options(
    db: AsyncSession = Depends(get_db)
):
    """获取筛选选项（无需登录）"""
    result = await experience_service.get_filter_options(db=db)
    return ApiResponse.success(data=result)


@router.get("/{experience_id}")
async def get_experience_detail(
    experience_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取面经详情（无需登录）"""
    result = await experience_service.get_experience_detail(
        db=db,
        experience_id=experience_id
    )
    return ApiResponse.success(data=result)


@router.post("/{experience_id}/like")
async def like_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db)
):
    """点赞面经（无需登录）"""
    result = await experience_service.like_experience(
        db=db,
        experience_id=experience_id
    )
    return ApiResponse.success(data=result)


@router.post("/{experience_id}/collect")
async def collect_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """收藏/取消收藏面经（需要登录）"""
    result = await experience_service.collect_experience(
        db=db,
        experience_id=experience_id,
        user_id=current_user.id
    )
    return ApiResponse.success(data=result)
