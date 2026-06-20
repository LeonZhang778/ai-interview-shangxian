from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import AuthBase
from app.db.session import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.response import ApiResponse

router = APIRouter()

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False
)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    payload = AuthBase.verify_token(token, scope="client")
    if not payload:
        return None
    user = await db.get(User, int(payload.get("sub")))
    return user if user and user.is_active else None


class SubmitFeedbackRequest(BaseModel):
    content: str
    feedback_type: str = "bug"
    contact: Optional[str] = None
    page_url: Optional[str] = None
    screenshot_url: Optional[str] = None


@router.post("")
async def submit_feedback(
    req: SubmitFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    feedback = Feedback(
        user_id=current_user.id if current_user else None,
        content=req.content,
        feedback_type=req.feedback_type,
        contact=req.contact,
        page_url=req.page_url,
        screenshot_url=req.screenshot_url,
        status="pending",
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return ApiResponse.success(data={"id": feedback.id})


@router.get("/my")
async def my_feedbacks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    if not current_user:
        return ApiResponse.failed(message="请先登录", body_code=1002, http_code=401)

    base_query = select(Feedback).where(Feedback.user_id == current_user.id)
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query)

    query = base_query.order_by(Feedback.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    items = [
        {
            "id": f.id,
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
