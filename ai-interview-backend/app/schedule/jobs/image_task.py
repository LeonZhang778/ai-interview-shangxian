import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.celery_app import celery_app
from app.core.config import settings
from app.models.image_task import ImageTask
from app.services.client.image_service import image_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="generate_image", max_retries=3)
def generate_image_task(self, task_id: int):
    """异步图片生成任务"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_process_task(task_id))
    finally:
        loop.close()


async def _process_task(task_id: int):
    db_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        task = None
        try:
            result = await db.execute(select(ImageTask).where(ImageTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.warning(f"Task {task_id} not found")
                return

            # 更新状态为 processing
            task.status = "processing"
            await db.commit()

            # 调用 Pollinations API 生成图片
            image_data = await image_service.generate_image(
                prompt=task.prompt,
                negative_prompt=task.negative_prompt,
                width=task.width,
                height=task.height,
            )

            # 保存图片到本地
            image_url = image_service.save_image(image_data, task_id)

            # 更新任务状态
            task.status = "success"
            task.image_url = image_url
            await db.commit()
            logger.info(f"Task {task_id} completed: {image_url}")

        except Exception as e:
            logger.exception(f"Generate image task {task_id} failed")
            try:
                if task:
                    task.status = "failed"
                    task.error_message = str(e)[:500]
                    await db.commit()
            except Exception as commit_err:
                logger.warning(f"Commit failed status for task {task_id}: {commit_err}")
                try:
                    await db.rollback()
                except Exception as rollback_err:
                    logger.warning(f"Rollback after commit failure failed (expected): {rollback_err}")
        finally:
            try:
                await engine.dispose()
            except Exception as dispose_err:
                logger.warning(f"Engine dispose failed: {dispose_err}")
