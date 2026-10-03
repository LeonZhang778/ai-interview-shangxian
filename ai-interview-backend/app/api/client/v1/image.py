from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.client.deps import get_current_user
from app.services.client.image_service import image_service
from app.schemas.client.image import ImageGenerate
from app.schemas.response import ApiResponse
from app.models.user import User
from app.exceptions.http_exceptions import APIException
from app.services.common.setting_service import get_setting_bool

router = APIRouter()


@router.post("/generate")
async def generate_image(
    data: ImageGenerate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交图片生成任务"""
    # 功能开关：后台可通过系统设置关闭 AI 生图
    if not await get_setting_bool("image_generation_enabled", True):
        # 使用 400 而非 403，避免前端拦截器将 403 判定为登录失效而强制登出
        raise APIException(
            code=10501,
            message="该生图功能已关闭请稍后再试~",
            status_code=400,
        )
    result = await image_service.create_task(
        db=db,
        user_id=current_user.id,
        prompt=data.prompt,
        negative_prompt=data.negative_prompt,
        width=data.width,
        height=data.height,
        steps=data.steps,
        cfg_scale=data.cfg_scale,
    )
    # 异步执行图片生成
    from app.schedule.jobs.image_task import generate_image_task
    try:
        generate_image_task.delay(result["task_id"])
    except Exception as exc:
        await image_service.mark_task_failed(
            db=db,
            task_id=result["task_id"],
            user_id=current_user.id,
            message="后台任务提交失败，请稍后重试",
        )
        raise APIException(code=10503, message="后台任务提交失败，请稍后重试", status_code=503) from exc
    return ApiResponse.success(data=result)


@router.get("/tasks")
async def get_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的图片任务列表"""
    result = await image_service.get_tasks(
        db=db,
        user_id=current_user.id,
        page=page,
        size=size,
    )
    return ApiResponse.success(data=result)


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个任务状态"""
    result = await image_service.get_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
    )
    return ApiResponse.success(data=result)


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除任务"""
    await image_service.delete_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
    )
    return ApiResponse.success(message="任务已删除")
