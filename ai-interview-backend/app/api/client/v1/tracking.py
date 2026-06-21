from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.models.page_view import PageView
from app.schemas.response import ApiResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class PageViewRequest(BaseModel):
    page_path: str
    session_id: Optional[str] = None


@router.post("/pageview")
async def track_pageview(
    body: PageViewRequest,
    background_tasks: BackgroundTasks,
):
    """记录页面浏览（公开接口，支持匿名）"""
    background_tasks.add_task(_save_pageview, body.page_path, body.session_id)
    return ApiResponse.success(data=None)


async def _save_pageview(page_path: str, session_id: Optional[str]):
    from app.db.session import async_session
    try:
        async with async_session() as db:
            pv = PageView(page_path=page_path, session_id=session_id)
            db.add(pv)
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to save pageview: {e}")
