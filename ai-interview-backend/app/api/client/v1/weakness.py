from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.weakness_service import weakness_service

router = APIRouter()


@router.get("/dashboard")
async def get_mistake_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await weakness_service.get_mistake_dashboard(db=db, user_id=current_user.id)
    return ApiResponse.success(data=result)


@router.get("/heatmap")
async def get_weakness_heatmap(
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await weakness_service.get_weakness_heatmap(
        db=db, user_id=current_user.id, limit=limit
    )
    return ApiResponse.success(data=result)


@router.get("/recommendations")
async def get_recommended_practice(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await weakness_service.get_recommended_practice(
        db=db, user_id=current_user.id, limit=limit
    )
    return ApiResponse.success(data=result)
