import asyncio
import logging

from app.core.celery_app import celery_app
from app.db.session import async_session
from app.services.client.resume_service import resume_service

logger = logging.getLogger(__name__)


@celery_app.task(name="resume.parse")
def parse_resume_task(resume_id: int, user_id: int):
    """异步解析简历，避免上传接口被 PDF/DOCX 解析和 AI 调用阻塞。"""
    return asyncio.run(_parse_resume(resume_id, user_id))


async def _parse_resume(resume_id: int, user_id: int):
    async with async_session() as db:
        try:
            await resume_service.parse_resume_record(db, resume_id, user_id)
            return {"resume_id": resume_id, "status": "completed"}
        except Exception as exc:
            logger.warning("简历解析任务失败: resume_id=%s user_id=%s error=%s", resume_id, user_id, exc)
            return {"resume_id": resume_id, "status": "failed"}
