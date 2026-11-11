import json
import logging
import os
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.resume import Resume
from app.services.client.ai_service import AIService
from app.services.client.document_parser import (
    ocr_docx_images_with_vlm,
    ocr_pdf_with_vlm,
    parse_document,
)
from app.core.config import settings
from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.utils.file_names import safe_uuid_filename
from app.utils.utils import safe_parse_json

logger = logging.getLogger(__name__)

# 简历上传目录
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件扩展名（与 document_parser 对齐）
ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".text")


class ResumeService:

    @staticmethod
    async def upload_and_parse(
        db: AsyncSession,
        user_id: int,
        file_content: bytes,
        file_name: str,
        target_position: str
    ) -> Dict:
        """上传简历文件并投递异步解析任务（支持 PDF / DOCX / TXT / MD）"""
        # 保存文件到本地
        display_name, storage_name = safe_uuid_filename(file_name, {"pdf", "docx", "txt", "md", "text"}, "pdf")
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
        """解析已上传的简历记录，供 Celery worker 调用。

        通过 document_parser 统一解析 PDF / DOCX / TXT / MD：多栏阅读顺序重排、
        表格转 Markdown、标题结构检测、扫描件检测；扫描件在开启多模态 OCR 时走
        VLM 兜底，否则给出清晰错误提示。
        """
        query = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await db.execute(query)
        resume = result.scalar_one_or_none()
        if not resume:
            raise NotFoundError(message="简历不存在")

        try:
            resume.status = "parsing"
            await db.commit()

            file_path = resume.file_url or ""
            doc = parse_document(file_path, resume.file_name or "")
            for w in doc.warnings:
                logger.warning(f"[resume-parse] {w}")

            # 扫描件兜底：开启多模态 OCR 时尝试识别，否则给出清晰错误
            if doc.is_scanned:
                if getattr(settings, "AI_OCR_ENABLED", False) and getattr(settings, "AI_VISION_MODEL", ""):
                    logger.info("[resume-parse] 检测到扫描件，尝试多模态 OCR 兜底")
                    ocr_pages = await ocr_pdf_with_vlm(
                        file_path,
                        settings.AI_VISION_MODEL,
                        page_numbers=doc.scanned_pages,
                    )
                    if ocr_pages and all(page in ocr_pages for page in doc.scanned_pages):
                        page_parts = []
                        for page_number, native_text in enumerate(doc.page_texts, start=1):
                            content = native_text.strip()
                            ocr_text = ocr_pages.get(page_number, "").strip()
                            if ocr_text:
                                content = "\n\n".join(
                                    part for part in (content, f"[OCR 补充]\n{ocr_text}") if part
                                )
                            if content:
                                page_parts.append(f"[第 {page_number} 页]\n{content}")
                        doc.text = "\n\n".join(page_parts)
                        doc.is_scanned = False
                        doc.scanned_pages = []
                        logger.info("[resume-parse] 多模态 OCR 兜底成功")
                if doc.is_scanned or not doc.text.strip():
                    raise ValidationError(
                        message="扫描页面 OCR 未完成。请上传可复制文字的 PDF、DOCX、TXT 或 MD；"
                                "如需 OCR，请确认服务端已安装 PDF 渲染器并启用视觉模型配置"
                    )

            if doc.source_type == "docx" and doc.image_payloads:
                if getattr(settings, "AI_OCR_ENABLED", False) and getattr(settings, "AI_VISION_MODEL", ""):
                    image_ocr_text = await ocr_docx_images_with_vlm(
                        doc.image_payloads,
                        settings.AI_VISION_MODEL,
                    )
                    if image_ocr_text:
                        doc.text = "\n\n".join(
                            part for part in (doc.text.strip(), image_ocr_text.strip()) if part
                        )
                else:
                    logger.warning(
                        "[resume-parse] DOCX 包含 %s 张内嵌图片，OCR 未启用，图片文字不会进入简历解析",
                        doc.image_count,
                    )

            resume_text = doc.text
            if not resume_text.strip() and not doc.tables:
                raise ValidationError(message="无法从简历文件中提取有效文本内容")

            parsed = await AIService.parse_resume(resume_text)
            resume.parsed_content = json.dumps(parsed, ensure_ascii=False)

            analysis = await AIService.analyze_resume(parsed, resume.target_position)
            resume.analysis = json.dumps(analysis, ensure_ascii=False)

            resume.status = "completed"
            await db.commit()
        except Exception as e:
            logger.error(f"简历解析失败: {e}")
            resume.status = "failed"
            await db.commit()
            raise

    @staticmethod
    def _extract_resume_text(file_path: str) -> str:
        """从简历文件提取纯文本（PDF / DOCX / TXT / MD），复用 document_parser。"""
        doc = parse_document(file_path, os.path.basename(file_path))
        return doc.text

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
