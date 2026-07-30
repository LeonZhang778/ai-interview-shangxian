import json
import logging
from typing import Optional, Dict, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.learning_note import LearningNote
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.exceptions.http_exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class LearningNoteService:

    @staticmethod
    async def get_my_notes(
        db: AsyncSession,
        user_id: int,
        note_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """获取当前用户的笔记列表"""
        conditions = [LearningNote.user_id == user_id]
        if note_type:
            conditions.append(LearningNote.note_type == note_type)
        if status:
            conditions.append(LearningNote.status == status)
        if keyword:
            conditions.append(LearningNote.title.ilike(f"%{keyword}%"))

        query = select(LearningNote).where(*conditions).order_by(desc(LearningNote.updated_at))
        total_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(total_query)

        offset = (page - 1) * size
        result = await db.execute(query.offset(offset).limit(size))
        notes = result.scalars().all()

        items = [
            {
                "id": n.id,
                "title": n.title,
                "note_type": n.note_type,
                "visibility": n.visibility,
                "status": n.status,
                "tags": n.tags,
                "source": n.source,
                "interview_id": n.interview_id,
                "view_count": n.view_count,
                "like_count": n.like_count,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in notes
        ]
        from math import ceil
        return {
            "items": items,
            "total": total,
            "per_page": size,
            "current_page": page,
            "last_page": ceil(total / size) if size > 0 else 0,
            "has_more": page < ceil(total / size) if size > 0 and total > 0 else False,
        }

    @staticmethod
    async def get_public_notes(
        db: AsyncSession,
        note_type: Optional[str] = None,
        keyword: Optional[str] = None,
        sort: str = "latest",
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """获取公开笔记广场"""
        conditions = [
            LearningNote.visibility == "public",
            LearningNote.status == "published"
        ]
        if note_type:
            conditions.append(LearningNote.note_type == note_type)
        if keyword:
            from sqlalchemy import or_
            conditions.append(or_(
                LearningNote.title.ilike(f"%{keyword}%"),
                LearningNote.content.ilike(f"%{keyword}%"),
                LearningNote.tags.ilike(f"%{keyword}%")
            ))

        if sort == "popular":
            query = select(LearningNote).where(*conditions).order_by(desc(LearningNote.view_count))
        else:
            query = select(LearningNote).where(*conditions).order_by(desc(LearningNote.created_at))

        total_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(total_query)

        offset = (page - 1) * size
        result = await db.execute(query.offset(offset).limit(size))
        notes = result.scalars().all()

        items = [
            {
                "id": n.id,
                "title": n.title,
                "note_type": n.note_type,
                "tags": n.tags,
                "view_count": n.view_count,
                "like_count": n.like_count,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ]
        from math import ceil
        return {
            "items": items,
            "total": total,
            "per_page": size,
            "current_page": page,
            "last_page": ceil(total / size) if size > 0 else 0,
            "has_more": page < ceil(total / size) if size > 0 and total > 0 else False,
        }

    @staticmethod
    async def get_note_detail(
        db: AsyncSession,
        note_id: int,
        user_id: Optional[int] = None
    ) -> Dict:
        """获取笔记详情"""
        note = await db.get(LearningNote, note_id)
        if not note:
            raise NotFoundError(message="笔记不存在")

        is_owner = note.user_id == user_id if user_id else False
        is_public = note.visibility == "public" and note.status == "published"
        if not is_owner and not is_public:
            raise NotFoundError(message="笔记不存在")

        # 非作者访问时增加浏览量
        if not is_owner:
            note.view_count = (note.view_count or 0) + 1
            await db.commit()
            # commit 会过期所有属性，async session 下再次访问会触发
            # lazy reload 并抛 MissingGreenlet，因此必须显式 refresh
            await db.refresh(note)

        return {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "note_type": note.note_type,
            "visibility": note.visibility,
            "status": note.status,
            "tags": note.tags,
            "source": note.source,
            "interview_id": note.interview_id,
            "view_count": note.view_count,
            "like_count": note.like_count,
            "is_owner": is_owner,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }

    @staticmethod
    async def create_note(
        db: AsyncSession,
        user_id: int,
        title: str,
        content: str = "",
        note_type: str = "note",
        visibility: str = "private",
        status: str = "draft",
        tags: Optional[str] = None,
        interview_id: Optional[int] = None,
        source: str = "manual"
    ) -> Dict:
        """创建笔记"""
        note = LearningNote(
            user_id=user_id,
            title=title,
            content=content,
            note_type=note_type,
            visibility=visibility,
            status=status,
            tags=tags,
            interview_id=interview_id,
            source=source,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return {"id": note.id, "title": note.title}

    @staticmethod
    async def update_note(
        db: AsyncSession,
        user_id: int,
        note_id: int,
        **kwargs
    ) -> Dict:
        """更新笔记"""
        note = await db.get(LearningNote, note_id)
        if not note:
            raise NotFoundError(message="笔记不存在")
        if note.user_id != user_id:
            raise ValidationError(message="无权修改此笔记")

        for key, value in kwargs.items():
            if value is not None and hasattr(note, key):
                setattr(note, key, value)
        await db.commit()
        return {"id": note.id, "message": "更新成功"}

    @staticmethod
    async def delete_note(
        db: AsyncSession,
        user_id: int,
        note_id: int
    ) -> Dict:
        """删除笔记"""
        note = await db.get(LearningNote, note_id)
        if not note:
            raise NotFoundError(message="笔记不存在")
        if note.user_id != user_id:
            raise ValidationError(message="无权删除此笔记")
        await db.delete(note)
        await db.commit()
        return {"message": "笔记已删除"}

    @staticmethod
    async def generate_from_interview(
        db: AsyncSession,
        user_id: int,
        interview_id: int,
        note_type: str = "review",
        title: Optional[str] = None,
        visibility: str = "private"
    ) -> Dict:
        """从 AI 面试结果生成学习笔记草稿（核心回流逻辑）"""
        # 获取面试记录
        interview = await db.get(Interview, interview_id)
        if not interview or interview.user_id != user_id:
            raise NotFoundError(message="面试记录不存在")
        if interview.status != "completed":
            raise ValidationError(message="面试尚未完成，无法生成笔记")

        # 检查是否已为该面试生成过笔记
        existing = await db.execute(
            select(LearningNote).where(
                LearningNote.interview_id == interview_id,
                LearningNote.user_id == user_id,
                LearningNote.source == "interview"
            )
        )
        existing_note = existing.scalar_one_or_none()
        if existing_note:
            return {
                "id": existing_note.id,
                "title": existing_note.title,
                "message": "该面试已有学习笔记，已为你打开"
            }

        # 获取面试对话和评分
        msg_query = select(InterviewMessage).where(
            InterviewMessage.interview_id == interview_id
        ).order_by(InterviewMessage.id)
        msg_result = await db.execute(msg_query)
        messages = msg_result.scalars().all()

        # 解析报告
        report = {}
        if interview.report:
            try:
                report = json.loads(interview.report)
            except json.JSONDecodeError:
                report = {}

        # 按题型组装 Markdown 内容
        content_parts = []
        content_parts.append(f"# {title or f'{interview.target_position} 面试复盘'}\n")
        content_parts.append(f"> 得分：**{float(interview.overall_score) if interview.overall_score else 0}/10**\n")
        content_parts.append(f"> 难度：{interview.difficulty} | 题数：{interview.total_questions}\n\n")

        if report.get("summary"):
            content_parts.append("## 总体评价\n")
            content_parts.append(f"{report['summary']}\n\n")

        if report.get("strengths"):
            content_parts.append("## 亮点\n")
            for s in report["strengths"]:
                content_parts.append(f"- {s}\n")
            content_parts.append("\n")

        if report.get("weaknesses"):
            content_parts.append("## 薄弱点\n")
            for w in report["weaknesses"]:
                content_parts.append(f"- {w}\n")
            content_parts.append("\n")

        if report.get("suggestions"):
            content_parts.append("## 改进建议\n")
            for s in report["suggestions"]:
                content_parts.append(f"- {s}\n")
            content_parts.append("\n")

        # 逐题问答（重点：错题标记）
        content_parts.append("## 逐题记录\n")
        candidate_msgs = [m for m in messages if m.role == "candidate"]
        for m in candidate_msgs:
            idx = m.question_index if m.question_index is not None else 0
            score = float(m.score) if m.score else 0
            tag = "❌ 错题" if score < 6.0 else "✅ 通过"
            content_parts.append(f"### 第{idx + 1}题 [{tag} | 得分 {score}/10]\n")
            content_parts.append(f"**我的回答：**\n{m.content}\n\n")
            if m.feedback:
                content_parts.append(f"**AI 评语：**\n{m.feedback}\n\n")

        # 如果是错题类型，额外生成薄弱知识点标签
        tags_str = None
        if note_type == "mistake" and report.get("weaknesses"):
            tags_str = ",".join(report["weaknesses"][:5])

        content = "\n".join(content_parts)

        note = LearningNote(
            user_id=user_id,
            title=title or f"{interview.target_position} 面试复盘",
            content=content,
            note_type=note_type,
            visibility=visibility,
            status="draft",
            tags=tags_str,
            interview_id=interview_id,
            source="interview",
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)

        return {
            "id": note.id,
            "title": note.title,
            "message": "学习笔记草稿已生成"
        }

    @staticmethod
    async def get_note_stats(
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """获取用户笔记统计（用于学习仪表盘）"""
        total = await db.scalar(
            select(func.count()).select_from(
                select(LearningNote).where(LearningNote.user_id == user_id).subquery()
            )
        )
        by_type = {}
        type_query = select(
            LearningNote.note_type,
            func.count(LearningNote.id)
        ).where(LearningNote.user_id == user_id).group_by(LearningNote.note_type)
        type_result = await db.execute(type_query)
        for t, c in type_result:
            by_type[t] = c

        return {
            "total": total or 0,
            "by_type": by_type,
        }


learning_note_service = LearningNoteService()
