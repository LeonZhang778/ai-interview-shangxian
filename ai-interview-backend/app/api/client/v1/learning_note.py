from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.learning_note_service import learning_note_service

router = APIRouter()


class NoteCreateBody(BaseModel):
    title: str
    content: str = ""
    note_type: str = "note"
    visibility: str = "private"
    status: str = "draft"
    tags: Optional[str] = None
    interview_id: Optional[int] = None


class NoteUpdateBody(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None


class NoteFromInterviewBody(BaseModel):
    interview_id: int
    title: Optional[str] = None
    note_type: str = "review"
    visibility: str = "private"


@router.get("/my")
async def get_my_notes(
    note_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_my_notes(
        db=db, user_id=current_user.id, note_type=note_type,
        status=status, keyword=keyword, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/public")
async def get_public_notes(
    note_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    sort: str = Query("latest"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_public_notes(
        db=db, note_type=note_type, keyword=keyword,
        sort=sort, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.post("")
async def create_note(
    body: NoteCreateBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.create_note(
        db=db, user_id=current_user.id,
        title=body.title, content=body.content,
        note_type=body.note_type, visibility=body.visibility,
        status=body.status, tags=body.tags,
        interview_id=body.interview_id
    )
    return ApiResponse.success(data=result)


@router.post("/from-interview")
async def generate_from_interview(
    body: NoteFromInterviewBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """从 AI 面试结果生成学习笔记草稿（核心回流接口）"""
    result = await learning_note_service.generate_from_interview(
        db=db, user_id=current_user.id,
        interview_id=body.interview_id,
        note_type=body.note_type, title=body.title,
        visibility=body.visibility
    )
    return ApiResponse.success(data=result, message=result.get("message", "生成成功"))


@router.get("/stats")
async def get_note_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_note_stats(db=db, user_id=current_user.id)
    return ApiResponse.success(data=result)


@router.get("/{note_id}")
async def get_note_detail(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_note_detail(
        db=db, note_id=note_id, user_id=current_user.id
    )
    return ApiResponse.success(data=result)


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    body: NoteUpdateBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.update_note(
        db=db, user_id=current_user.id, note_id=note_id,
        **body.model_dump(exclude_unset=True)
    )
    return ApiResponse.success(data=result)


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.delete_note(
        db=db, user_id=current_user.id, note_id=note_id
    )
    return ApiResponse.success(message=result["message"])
