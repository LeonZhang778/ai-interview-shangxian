from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.api.backoffice.deps import get_current_admin
from app.models.admin import Admin
from app.models.feedback import Feedback
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("")
async def list_feedbacks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    feedback_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    query = select(Feedback).order_by(Feedback.created_at.desc())
    count_query = select(func.count()).select_from(Feedback)

    if status:
        query = query.where(Feedback.status == status)
        count_query = count_query.where(Feedback.status == status)
    if feedback_type:
        query = query.where(Feedback.feedback_type == feedback_type)
        count_query = count_query.where(Feedback.feedback_type == feedback_type)

    total = await db.scalar(count_query)
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    items = [
        {
            "id": f.id,
            "user_id": f.user_id,
            "content": f.content,
            "feedback_type": f.feedback_type,
            "contact": f.contact,
            "page_url": f.page_url,
            "screenshot_url": f.screenshot_url,
            "status": f.status,
            "admin_reply": f.admin_reply,
            "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]

    return ApiResponse.success(data={"items": items, "total": total, "page": page, "per_page": per_page})


@router.get("/stats")
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    result = await db.execute(
        select(Feedback.status, func.count()).group_by(Feedback.status)
    )
    stats = {row[0]: row[1] for row in result.all()}
    return ApiResponse.success(data={
        "pending": stats.get("pending", 0),
        "processing": stats.get("processing", 0),
        "resolved": stats.get("resolved", 0),
        "ignored": stats.get("ignored", 0),
        "total": sum(stats.values()),
    })


@router.put("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        return ApiResponse.failed(message="反馈不存在", body_code=404, http_code=404)

    feedback.status = status
    if status == "resolved":
        feedback.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse.success(data={"id": feedback.id, "status": feedback.status})


@router.put("/{feedback_id}/reply")
async def reply_feedback(
    feedback_id: int,
    admin_reply: str,
    db: AsyncSession = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    feedback = await db.get(Feedback, feedback_id)
    if not feedback:
        return ApiResponse.failed(message="反馈不存在", body_code=404, http_code=404)

    feedback.admin_reply = admin_reply
    feedback.status = "resolved"
    feedback.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return ApiResponse.success(data={"id": feedback.id})
