import json
import logging
import os
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.utils.file_names import safe_uuid_filename
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)

# 简历上传目录
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ResumeService:

    @staticmethod
    async def upload_and_parse(
        db: AsyncSession,
        user_id: int,
        file_content: bytes,
        file_name: str,
        target_position: str
    ) -> Dict:
        """上传简历文件并投递异步解析任务"""
        # 保存文件到本地
        display_name, storage_name = safe_uuid_filename(file_name, {"pdf", "docx"}, "pdf")
        user_dir = os.path.join(UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, storage_name)
        with open(file_path, "wb") as f:
            f.write(file_content)

        # 创建简历记录
        resume = Resume(
            user_id=user_id,
            file_url=file_path,
            file_name=display_name,
            target_position=target_position,
            status="parsing"
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)  
        #把数据库里刚生成的完整数据，重新刷新到这个 resume 对象里，让它变成 “完整可用” 的

        try:
            from app.schedule.jobs.resume_tasks import parse_resume_task
            parse_resume_task.delay(resume.id, user_id)
        except Exception as e:
            logger.warning("简历解析任务投递失败: %s", e)
            resume.status = "failed"
            await db.commit()
            raise ValidationError(message="简历解析任务创建失败，请稍后重试")

        return {
            "resume_id": resume.id,
            "status": resume.status,
            "message": "简历上传成功，正在异步解析"
        }

    @staticmethod
    async def parse_resume_record(db: AsyncSession, resume_id: int, user_id: int) -> None:
        """解析已上传的简历记录，供 Celery worker 调用。"""
        query = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await db.execute(query)
        resume = result.scalar_one_or_none()
        if not resume:
            raise NotFoundError(message="简历不存在")

        try:
            resume.status = "parsing"
            await db.commit()

            resume_text = ResumeService._extract_resume_text(resume.file_url or "")
            if not resume_text.strip():
                raise ValidationError(message="无法从简历文件中提取文本内容")

            parsed = await AIService.parse_resume(resume_text)
            resume.parsed_content = json.dumps(parsed, ensure_ascii=False)

            analysis = await AIService.analyze_resume(parsed, resume.target_position)
            resume.analysis = json.dumps(analysis, ensure_ascii=False)

            resume.status = "completed"
            await db.commit()
        except Exception as e:
            logger.error(f"AI 简历解析失败: {e}")
            resume.status = "failed"
            await db.commit()
            raise

    @staticmethod
    def _extract_resume_text(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return ResumeService._extract_pdf_text(file_path)
        if ext == ".docx":
            return ResumeService._extract_docx_text(file_path)
        raise ValidationError(message="仅支持 PDF 或 DOCX 格式文件")

    @staticmethod
    def _extract_pdf_text(file_path: str) -> str:
        """从 PDF 文件中提取文本内容"""
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    @staticmethod
    def _extract_docx_text(file_path: str) -> str:
        """从 DOCX 文件中提取文本内容"""
        from docx import Document
        document = Document(file_path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)

    @staticmethod
    async def get_resume(db: AsyncSession, resume_id: int, user_id: int) -> Dict:
        """根据 ID 获取简历详情"""
        query = select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id
        )
        result = await db.execute(query)
        resume = result.scalar_one_or_none()

        if not resume:
            raise NotFoundError(message="简历不存在")

        parsed_content = safe_parse_json(resume.parsed_content, None)
        analysis = safe_parse_json(resume.analysis, None)

        return {
            "resume_id": resume.id,
            "status": resume.status,
            "file_name": resume.file_name,
            "target_position": resume.target_position,
            "parsed_content": parsed_content,
            "analysis": analysis,
            "created_at": resume.created_at.isoformat() if resume.created_at else None
        }

    @staticmethod
    async def get_user_resumes(db: AsyncSession, user_id: int) -> list:
        """获取用户的所有简历列表"""
        query = select(Resume).where(
            Resume.user_id == user_id
        ).order_by(Resume.created_at.desc())
        result = await db.execute(query)
        resumes = result.scalars().all()

        return [
            {
                "resume_id": r.id,
                "file_name": r.file_name,
                "target_position": r.target_position,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in resumes
        ]


resume_service = ResumeService()
