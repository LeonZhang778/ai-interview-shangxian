from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.feedback import Feedback
from app.schemas.response import ApiResponse

router = APIRouter()


@router.post("")
async def submit_feedback(
    content: str,
    feedback_type: str = "bug",
    contact: str = None,
    page_url: str = None,
    screenshot_url: str = None,
    db: AsyncSession = Depends(get_db),
):
    feedback = Feedback(
        content=content,
        feedback_type=feedback_type,
        contact=contact,
        page_url=page_url,
        screenshot_url=screenshot_url,
        status="pending",
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return ApiResponse.success(data={"id": feedback.id})
