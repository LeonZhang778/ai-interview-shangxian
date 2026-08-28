from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.services.client.experience_service import experience_service
from app.schemas.response import ApiResponse
from app.common.audit import log_audit

router = APIRouter()


class BatchReviewRequest(BaseModel):
    ids: List[int]
    action: str


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

    # 发送审核结果通知
    try:
        from app.models.experience import Experience
        exp = await db.get(Experience, experience_id)
        if exp and exp.author_id:
            from app.services.client.notification_service import notification_service
            if action == "approve":
                await notification_service.enqueue_notification(
                    db=db, user_id=exp.author_id,
                    title="面经审核通过",
                    content=f"你投稿的「{exp.title}」已通过审核，快去看看吧",
                    notification_type="experience",
                    related_id=experience_id, related_type="experience"
                )
            elif action == "reject":
                await notification_service.enqueue_notification(
                    db=db, user_id=exp.author_id,
                    title="面经审核未通过",
                    content=f"你投稿的「{exp.title}」未通过审核，请修改后重新投稿",
                    notification_type="experience",
                    related_id=experience_id, related_type="experience"
                )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"发送审核通知失败: {e}")

    return ApiResponse.success(data=result)


@router.delete("/{experience_id}")
async def delete_experience(
    experience_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """删除面经"""
    result = await experience_service.admin_delete_experience(
        db=db, experience_id=experience_id
    )

    await log_audit(db, current_admin.id, "delete", "experience", experience_id,
                    f"删除面经: {result['title']}")

    return ApiResponse.success(data=result)


@router.post("/batch-review")
async def batch_review(
    body: BatchReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    """批量审核/删除面经"""
    result = await experience_service.admin_batch_review(
        db=db, experience_ids=body.ids, action=body.action
    )

    action_label = {"approve": "批量通过", "reject": "批量拒绝", "delete": "批量删除"}.get(body.action, body.action)
    await log_audit(db, current_admin.id, "batch_review", "experience", None,
                    f"{action_label} {result['affected']} 条面经")

    return ApiResponse.success(data=result)
