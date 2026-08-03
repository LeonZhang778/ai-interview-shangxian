import os
import uuid
import mimetypes
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field, field_validator

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.models.learning_note import LearningNote
from app.models.notebook import Notebook
from app.schemas.response import ApiResponse
from app.services.client.learning_note_service import learning_note_service
from sqlalchemy import select

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


class TagApplyBody(BaseModel):
    """应用 AI 推荐标签时提交的标签列表"""
    tags: list[str] = Field(..., min_length=1, max_length=5)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        cleaned = [tag.strip() for tag in value if tag and tag.strip()]
        if not cleaned:
            raise ValueError("至少需要一个有效标签")
        if any(len(tag) > 20 for tag in cleaned):
            raise ValueError("单个标签不能超过 20 个字符")
        return list(dict.fromkeys(cleaned))[:5]


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


@router.post("/{note_id}/summary")
async def generate_note_summary(
    note_id: int,
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成或获取笔记的 AI 摘要（含三级要点）"""
    result = await learning_note_service.generate_summary(
        db=db, note_id=note_id, user_id=current_user.id, force=force
    )
    return ApiResponse.success(data=result)


@router.post("/{note_id}/suggest-tags")
async def suggest_note_tags(
    note_id: int,
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 推荐的标签（不写入笔记，仅返回建议）"""
    result = await learning_note_service.suggest_tags(
        db=db, note_id=note_id, user_id=current_user.id, force=force
    )
    return ApiResponse.success(data=result)


@router.post("/{note_id}/apply-tags")
async def apply_suggested_tags(
    note_id: int,
    body: TagApplyBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """应用 AI 推荐的标签（用户确认后写入笔记）"""
    # 标准化提交的标签，避免前端绕过标准化
    from app.utils.utils import normalize_tag
    tags = list(dict.fromkeys(
        normalize_tag(t) for t in body.tags if t and t.strip()
    ))[:5]
    result = await learning_note_service.update_note(
        db=db, user_id=current_user.id, note_id=note_id, tags=",".join(tags)
    )
    return ApiResponse.success(data={"tags": tags, "message": "标签已应用"})


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


def _safe_filename(value: str, fallback: str) -> str:
    """清理下载文件名，避免路径穿越和响应头编码异常。"""
    cleaned = "".join(
        char for char in (value or "")
        if char not in '\\/:*?"<>|' and ord(char) >= 32 and ord(char) != 127
    ).strip()
    return cleaned or fallback


def _content_disposition(filename: str) -> str:
    """同时提供 ASCII 回退名和 RFC 5987 UTF-8 文件名。"""
    ascii_name = "".join(char if ord(char) < 128 else "_" for char in filename)
    ascii_name = ascii_name.replace('"', "'") or "download"
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'


def _note_markdown(note: LearningNote) -> str:
    """将笔记转换为可独立阅读的 Markdown。"""
    updated_at = note.updated_at.strftime("%Y-%m-%d %H:%M") if note.updated_at else "N/A"
    parts = [f"# {note.title}", ""]
    if note.tags:
        parts.extend([f"> 标签: {note.tags}", ""])
    parts.extend([f"> 更新时间: {updated_at}", "", "---", "", note.content or ""])
    return "\n".join(parts)


async def _collect_notebook_ids(db: AsyncSession, root_id: int, user_id: int) -> tuple[Notebook | None, list[int]]:
    """校验根笔记本归属，并安全收集其所有子孙笔记本。"""
    root = await db.get(Notebook, root_id)
    if not root or root.user_id != user_id:
        return None, []

    notebook_ids = [root_id]
    pending = [root_id]
    visited = {root_id}
    while pending:
        result = await db.execute(
            select(Notebook.id).where(
                Notebook.user_id == user_id,
                Notebook.parent_id.in_(pending),
            )
        )
        children = [row[0] for row in result.all() if row[0] not in visited]
        visited.update(children)
        notebook_ids.extend(children)
        pending = children
    return root, notebook_ids


@router.get("/{note_id}/export")
async def export_single_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出单个笔记为 Markdown 文件。"""
    from fastapi.responses import StreamingResponse
    import io

    note = await db.get(LearningNote, note_id)
    if not note or note.user_id != current_user.id:
        return ApiResponse.failed(message="笔记不存在", body_code=404)

    filename = f"{_safe_filename(note.title, f'note_{note_id}')}.md"
    return StreamingResponse(
        io.BytesIO(_note_markdown(note).encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


async def _export_notes_zip(
    db: AsyncSession,
    user_id: int,
    notebook_ids: list[int] | None = None,
) -> tuple[bytes | None, str | None]:
    """生成笔记 ZIP，返回二进制内容和空结果错误信息。"""
    import io
    import zipfile

    conditions = [LearningNote.user_id == user_id]
    if notebook_ids is not None:
        conditions.append(LearningNote.notebook_id.in_(notebook_ids))

    result = await db.execute(
        select(LearningNote, Notebook.name)
        .outerjoin(Notebook, LearningNote.notebook_id == Notebook.id)
        .where(*conditions)
        .order_by(LearningNote.notebook_id, LearningNote.created_at)
    )
    rows = result.all()
    if not rows:
        return None, "该笔记本下没有可导出的笔记" if notebook_ids is not None else "没有可导出的笔记"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        used_names: set[str] = set()
        for note, notebook_name in rows:
            folder = _safe_filename(notebook_name or "未分类", "未分类")
            title = _safe_filename(note.title, f"note_{note.id}")
            filename = f"{folder}/{title}.md"
            index = 1
            while filename in used_names:
                filename = f"{folder}/{title}_{index}.md"
                index += 1
            used_names.add(filename)
            archive.writestr(filename, _note_markdown(note))
    return buf.getvalue(), None


@router.get("/export/notebook/{notebook_id}")
async def export_notebook(
    notebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出整个笔记本（含子笔记本）为 ZIP 文件。"""
    from fastapi.responses import StreamingResponse
    import io

    root, notebook_ids = await _collect_notebook_ids(db, notebook_id, current_user.id)
    if not root:
        return ApiResponse.failed(message="笔记本不存在", body_code=404)

    content, error = await _export_notes_zip(db, current_user.id, notebook_ids)
    if error:
        return ApiResponse.failed(message=error, body_code=400)

    filename = f"{_safe_filename(root.name, f'notebook_{notebook_id}')}.zip"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/zip",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/export/all")
async def export_all_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出当前用户的全部笔记为 ZIP 文件。"""
    from fastapi.responses import StreamingResponse
    import io

    content, error = await _export_notes_zip(db, current_user.id)
    if error:
        return ApiResponse.failed(message=error, body_code=400)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/zip",
        headers={"Content-Disposition": _content_disposition("all_notes.zip")},
    )
