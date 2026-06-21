from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.client.interview_service import interview_service
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/{share_token}")
async def get_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    """通过分享链接查看面试报告（公开接口）"""
    result = await interview_service.get_shared_report(
        db=db,
        share_token=share_token
    )
    return ApiResponse.success(data=result)
