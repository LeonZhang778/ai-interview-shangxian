import os
import uuid
import mimetypes
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.learning_note_service import learning_note_service

router = APIRouter()

NOTE_IMAGE_DIR = "uploads/notes"
os.makedirs(NOTE_IMAGE_DIR, exist_ok=True)


class NoteCreateBody(BaseModel):
    title: str
    content: str = ""
    note_type: str = "note"
    visibility: str = "private"
    status: str = "draft"
    tags: Optional[str] = None
    notebook_id: Optional[int] = None
    interview_id: Optional[int] = None


class NoteUpdateBody(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    visibility: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None
    notebook_id: Optional[int] = None


class NoteFromInterviewBody(BaseModel):
    interview_id: int
    title: Optional[str] = None
    note_type: str = "review"
    visibility: str = "private"


@router.post("/upload-image")
async def upload_note_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传笔记中的图片，返回可访问的 URL"""
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        return ApiResponse.failed(message=f"不支持的文件类型: {content_type}", body_code=400)

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB
        return ApiResponse.failed(message="图片大小不能超过 5MB", body_code=400)

    ext = mimetypes.guess_extension(content_type) or ".png"
    filename = f"{current_user.id}/{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(NOTE_IMAGE_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/uploads/notes/{filename}"
    return ApiResponse.success(data={"url": url})


@router.get("/search")
async def search_notes(
    keyword: str = Query(..., min_length=1, max_length=100),
    note_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    scope: str = Query("my"),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """全文搜索笔记（支持 my 和 public 两种范围）"""
    if scope == "my" and not current_user:
        return ApiResponse.failed(message="需要登录才能搜索我的笔记", body_code=401)
    user_id = current_user.id if current_user else None
    result = await learning_note_service.search_notes(
        db=db, keyword=keyword, user_id=user_id,
        note_type=note_type, page=page, size=size, scope=scope,
    )
    return ApiResponse.success(data=result)


@router.get("/my")
async def get_my_notes(
    note_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    notebook_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_my_notes(
        db=db, user_id=current_user.id, note_type=note_type,
        status=status, keyword=keyword,
        notebook_id=notebook_id, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/public")
async def get_public_notes(
    note_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    sort: str = Query("latest"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_public_notes(
        db=db, note_type=note_type, keyword=keyword, tag=tag,
        sort=sort, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/public/tags")
async def get_public_tags(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """获取公开笔记的热门标签列表，供广场下拉筛选"""
    result = await learning_note_service.get_popular_tags(db=db, limit=limit)
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
        notebook_id=body.notebook_id,
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
    status: Optional[str] = Query(None),
    notebook_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_note_stats(
        db=db, user_id=current_user.id, status=status, notebook_id=notebook_id
    )
    return ApiResponse.success(data=result)


@router.get("/{note_id}")
async def get_note_detail(
    note_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    result = await learning_note_service.get_note_detail(
        db=db, note_id=note_id, user_id=current_user.id if current_user else None
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
