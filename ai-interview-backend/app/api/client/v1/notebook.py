from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.client.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.client.notebook_service import notebook_service

router = APIRouter()


class NotebookCreateBody(BaseModel):
    name: str
    parent_id: Optional[int] = None
    icon: Optional[str] = None


class NotebookUpdateBody(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("")
async def get_notebooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的笔记本树（嵌套树 + 扁平列表）"""
    result = await notebook_service.get_tree(db=db, user_id=current_user.id)
    return ApiResponse.success(data=result)


@router.post("")
async def create_notebook(
    body: NotebookCreateBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建笔记本"""
    result = await notebook_service.create(
        db=db,
        user_id=current_user.id,
        name=body.name,
        parent_id=body.parent_id,
        icon=body.icon,
    )
    return ApiResponse.success(data=result)


@router.put("/{notebook_id}")
async def update_notebook(
    notebook_id: int,
    body: NotebookUpdateBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新笔记本"""
    result = await notebook_service.update(
        db=db,
        user_id=current_user.id,
        notebook_id=notebook_id,
        **body.model_dump(exclude_unset=True),
    )
    return ApiResponse.success(data=result)


@router.delete("/{notebook_id}")
async def delete_notebook(
    notebook_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除笔记本"""
    result = await notebook_service.delete(
        db=db, user_id=current_user.id, notebook_id=notebook_id
    )
    return ApiResponse.success(message=result["message"])