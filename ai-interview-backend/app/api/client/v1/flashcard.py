from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.flashcard_service import flashcard_service

router = APIRouter()


class ReviewBody(BaseModel):
    quality: int = Field(..., ge=0, le=5)


@router.get("")
async def list_cards(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await flashcard_service.list_cards(
        db=db, user_id=current_user.id, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/due")
async def get_due_cards(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await flashcard_service.get_due_cards(
        db=db, user_id=current_user.id, limit=limit
    )
    return ApiResponse.success(data=result)


@router.get("/stats")
async def get_flashcard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await flashcard_service.get_stats(db=db, user_id=current_user.id)
    return ApiResponse.success(data=result)


@router.post("/generate/{note_id}")
async def generate_cards(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await flashcard_service.generate_from_note(
        db=db, user_id=current_user.id, note_id=note_id
    )
    return ApiResponse.success(data=result)


@router.post("/{card_id}/review")
async def review_card(
    card_id: int,
    body: ReviewBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await flashcard_service.review_card(
        db=db, user_id=current_user.id, card_id=card_id, quality=body.quality
    )
    return ApiResponse.success(data=result)
