from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.services.client.experience_service import experience_service
from app.services.client.interview_service import interview_service
from app.schemas.response import ApiResponse
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_experiences(
    company: Optional[str] = Query(None, description="公司筛选"),
    position: Optional[str] = Query(None, description="岗位筛选"),
    level: Optional[str] = Query(None, description="经验级别"),
    round: Optional[str] = Query(None, description="面试轮次"),
    sort: str = Query("latest", description="排序: latest/popular/collected"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取面经列表（无需登录）"""
    result = await experience_service.get_experiences(
        db=db,
        company=company,
        position=position,
        level=level,
        round_=round,
        sort=sort,
        page=page,
        size=size
    )
    return ApiResponse.success(data=result)


@router.get("/filters")
async def get_filter_options(
    db: AsyncSession = Depends(get_db)
):
    """获取筛选选项（无需登录）"""
    result = await experience_service.get_filter_options(db=db)
    return ApiResponse.success(data=result)


class ExperienceSubmit(BaseModel):
    title: str
    company: str
    position: str
    content: str
    level: Optional[str] = None
    round: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[list] = None
    is_anonymous: bool = False


@router.post("/submit")
async def submit_experience(
    body: ExperienceSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交面经投稿（需要登录）"""
    result = await experience_service.submit_experience(
        db=db,
        user_id=current_user.id,
        title=body.title,
        company=body.company,
        position=body.position,
        content=body.content,
        level=body.level,
        round_=body.round,
        summary=body.summary,
        tags=body.tags,
        is_anonymous=body.is_anonymous,
    )
    return ApiResponse.success(data=result)


@router.get("/my/submissions")
async def get_my_experiences(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的投稿列表（需要登录）"""
    result = await experience_service.get_my_experiences(
        db=db, user_id=current_user.id, page=page, size=size
    )
    return ApiResponse.success(data=result)


# ==================== 收藏夹分组 ====================

class CollectionGroupCreate(BaseModel):
    name: str


class CollectionGroupUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class CollectionMove(BaseModel):
    group_id: Optional[int] = None


@router.get("/collections/my")
async def get_my_collections(
    group_id: Optional[int] = Query(None, description="分组ID筛选，0=未分组"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的收藏列表（需要登录）"""
    result = await experience_service.get_user_collections(
        db=db, user_id=current_user.id, group_id=group_id, page=page, size=size
    )
    return ApiResponse.success(data=result)


@router.get("/collections/groups")
async def get_collection_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的收藏分组列表（需要登录）"""
    result = await experience_service.get_collection_groups(db=db, user_id=current_user.id)
    return ApiResponse.success(data=result)


@router.post("/collections/groups")
async def create_collection_group(
    body: CollectionGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建收藏分组（需要登录）"""
    result = await experience_service.create_collection_group(
        db=db, user_id=current_user.id, name=body.name
    )
    return ApiResponse.success(data=result)


@router.put("/collections/groups/{group_id}")
async def update_collection_group(
    group_id: int,
    body: CollectionGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新收藏分组（需要登录）"""
    result = await experience_service.update_collection_group(
        db=db, user_id=current_user.id, group_id=group_id,
        name=body.name, sort_order=body.sort_order
    )
    return ApiResponse.success(data=result)


@router.delete("/collections/groups/{group_id}")
async def delete_collection_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除收藏分组（需要登录）"""
    result = await experience_service.delete_collection_group(
        db=db, user_id=current_user.id, group_id=group_id
    )
    return ApiResponse.success(data=result)


@router.put("/collections/{experience_id}/move")
async def move_collection(
    experience_id: int,
    body: CollectionMove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """移动收藏到指定分组（需要登录）"""
    result = await experience_service.move_collection(
        db=db, user_id=current_user.id, experience_id=experience_id, group_id=body.group_id
    )
    return ApiResponse.success(data=result)


@router.get("/{experience_id}")
async def get_experience_detail(
    experience_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取面经详情（无需登录）"""
    result = await experience_service.get_experience_detail(
        db=db,
        experience_id=experience_id
    )
    return ApiResponse.success(data=result)


class PracticeRequest(BaseModel):
    question_count: int = 5


@router.post("/{experience_id}/practice")
async def start_practice(
    experience_id: int,
    body: PracticeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """基于面经创建模拟面试"""
    result = await interview_service.start_practice_from_experience(
        db=db,
        user_id=current_user.id,
        experience_id=experience_id,
        question_count=body.question_count
    )
    return ApiResponse.success(data=result)


@router.post("/{experience_id}/like")
async def like_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """点赞/取消点赞面经（需要登录）"""
    result = await experience_service.like_experience(
        db=db,
        experience_id=experience_id,
        user_id=current_user.id
    )
    return ApiResponse.success(data=result)


@router.post("/{experience_id}/collect")
async def collect_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """收藏/取消收藏面经（需要登录）"""
    result = await experience_service.collect_experience(
        db=db,
        experience_id=experience_id,
        user_id=current_user.id
    )
    return ApiResponse.success(data=result)


@router.get("/{experience_id}/comments")
async def get_comments(
    experience_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """获取评论列表（无需登录）"""
    result = await experience_service.get_comments(
        db=db, experience_id=experience_id, page=page, size=size
    )
    return ApiResponse.success(data=result)


class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None


@router.post("/{experience_id}/comments")
async def create_comment(
    experience_id: int,
    body: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发表评论（需要登录）"""
    result = await experience_service.create_comment(
        db=db, experience_id=experience_id,
        user_id=current_user.id, content=body.content,
        parent_id=body.parent_id
    )
    return ApiResponse.success(data=result)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除自己的评论（需要登录）"""
    await experience_service.delete_comment(
        db=db, comment_id=comment_id, user_id=current_user.id
    )
    return ApiResponse.success(message="评论已删除")


@router.get("/{experience_id}/interaction-status")
async def get_interaction_status(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户对某面经的互动状态（需要登录）"""
    liked = await experience_service.check_user_liked(db, current_user.id, experience_id)
    collected = await experience_service.check_user_collected(db, current_user.id, experience_id)
    return ApiResponse.success(data={"liked": liked, "collected": collected})
