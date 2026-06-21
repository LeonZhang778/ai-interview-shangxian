from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.services.client.experience_service import experience_service
from app.schemas.response import ApiResponse
from app.common.audit import log_audit

router = APIRouter()


@router.get("")
async def list_experiences(
    status: Optional[str] = Query(None, description="状态筛选: pending/published/rejected"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取面经列表（管理员）"""
    result = await experience_service.admin_list_experiences(
        db=db, status=status, page=page, size=per_page
    )
    return ApiResponse.success(data=result)


@router.get("/{experience_id}")
async def get_experience_detail(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """获取面经详情（管理员）"""
    result = await experience_service.admin_get_experience_detail(
        db=db, experience_id=experience_id
    )
    return ApiResponse.success(data=result)


@router.put("/{experience_id}/review")
async def review_experience(
    experience_id: int,
    action: str = Query(..., description="approve 或 reject"),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """审核面经"""
    result = await experience_service.admin_review_experience(
        db=db, experience_id=experience_id, action=action
    )

    action_label = "通过" if action == "approve" else "拒绝"
    await log_audit(db, current_admin.id, "review", "experience", experience_id,
                    f"{action_label}面经审核: ID {experience_id}")

    return ApiResponse.success(data=result)
