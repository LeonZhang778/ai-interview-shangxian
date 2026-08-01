import json
import logging
from math import ceil
from typing import Optional, Dict, List
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.learning_note import LearningNote
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.prompts.learning_note import NOTE_SUMMARIZE_PROMPT, NOTE_TAG_SUGGEST_PROMPT
from app.utils.utils import normalize_tag

logger = logging.getLogger(__name__)


class LearningNoteService:

    @staticmethod
    async def search_notes(
        db: AsyncSession,
        keyword: str,
        user_id: Optional[int] = None,
        note_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        scope: str = "my",
    ) -> Dict:
        """
        全文搜索笔记（使用 PostgreSQL tsvector）

        Args:
            keyword: 搜索关键词
            user_id: 用户 ID（scope=my 时必填）
            note_type: 按类型筛选
            page: 页码
            size: 每页条数
            scope: "my" 搜索我的笔记，"public" 搜索公开广场
        """
        query_vec = func.plainto_tsquery("simple", keyword)

        conditions = [
            LearningNote.search_vector.op("@@")(query_vec),
        ]

        if scope == "my" and user_id:
            conditions.append(LearningNote.user_id == user_id)
        elif scope == "public":
            conditions.append(LearningNote.visibility == "public")
            conditions.append(LearningNote.status == "published")

        if note_type:
            conditions.append(LearningNote.note_type == note_type)

        # 相关性排序
        rank = func.ts_rank(LearningNote.search_vector, query_vec)

        # 高亮片段
        headline = func.ts_headline(
            "simple",
            LearningNote.content,
            query_vec,
            "MaxWords=40, MinWords=15, StartSel=<mark>, StopSel=</mark>",
        )

        query = (
            select(
                LearningNote,
                rank.label("relevance"),
                headline.label("headline"),
            )
            .where(*conditions)
            .order_by(desc("relevance"))
        )

        # 总数
        total_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(total_query) or 0

        # 分页
        offset = (page - 1) * size
        result = await db.execute(query.offset(offset).limit(size))
        rows = result.all()

        items = []
        for row in rows:
            note = row[0]
            items.append({
                "id": note.id,
                "title": note.title,
                "note_type": note.note_type,
                "tags": note.tags,
                "view_count": note.view_count,
                "like_count": note.like_count,
                "relevance": float(row.relevance) if row.relevance else 0,
                "headline": row.headline or "",
                "created_at": note.created_at.isoformat() if note.created_at else None,
            })

        return {
            "items": items,
            "total": total,
            "per_page": size,
            "current_page": page,
            "last_page": ceil(total / size) if size > 0 else 0,
            "has_more": page < ceil(total / size) if size > 0 and total > 0 else False,
        }

    @staticmethod
    async def get_my_notes(
        db: AsyncSession,
        user_id: int,
        note_type: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        notebook_id: Optional[int] = None,
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
        if notebook_id is not None:
            conditions.append(LearningNote.notebook_id == notebook_id)

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
                "notebook_id": n.notebook_id,
                "interview_id": n.interview_id,
                "view_count": n.view_count,
                "like_count": n.like_count,
                "summary": n.summary,
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
        tag: Optional[str] = None,
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
        if tag:
            # tags 以逗号分隔存储，按单个标签精确匹配
            conditions.append(or_(
                LearningNote.tags == tag,
                LearningNote.tags.ilike(f"{tag},%"),
                LearningNote.tags.ilike(f"%,{tag}"),
                LearningNote.tags.ilike(f"%,{tag},%"),
            ))
        if keyword:
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
                "summary": n.summary,
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
    async def get_popular_tags(db: AsyncSession, limit: int = 50) -> List[Dict]:
        """获取公开笔记中出现过的热门标签（按使用次数排序）"""
        rows = await db.execute(
            select(LearningNote.tags)
            .where(
                LearningNote.visibility == "public",
                LearningNote.status == "published",
                LearningNote.tags.isnot(None),
                LearningNote.tags != "",
            )
            .order_by(desc(LearningNote.view_count))
            .limit(500)
        )
        tag_count: Dict[str, int] = {}
        for (tags_str,) in rows:
            if not tags_str:
                continue
            for t in tags_str.split(","):
                t = t.strip()
                if t:
                    tag_count[t] = tag_count.get(t, 0) + 1
        # 按使用次数排序，取前 limit 个
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"name": name, "count": cnt} for name, cnt in sorted_tags]

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
            "notebook_id": note.notebook_id,
            "interview_id": note.interview_id,
            "view_count": note.view_count,
            "like_count": note.like_count,
            "summary": note.summary,
            "key_points": json.loads(note.key_points) if note.key_points else [],
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
        notebook_id: Optional[int] = None,
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
            notebook_id=notebook_id,
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
        user_id: int,
        status: Optional[str] = None,
        notebook_id: Optional[int] = None,
    ) -> Dict:
        """获取用户笔记统计（用于学习仪表盘）"""
        base_conditions = [LearningNote.user_id == user_id]
        if status:
            base_conditions.append(LearningNote.status == status)
        if notebook_id is not None:
            base_conditions.append(LearningNote.notebook_id == notebook_id)

        total = await db.scalar(
            select(func.count()).select_from(
                select(LearningNote).where(*base_conditions).subquery()
            )
        )
        by_type = {}
        type_query = select(
            LearningNote.note_type,
            func.count(LearningNote.id)
        ).where(*base_conditions).group_by(LearningNote.note_type)
        type_result = await db.execute(type_query)
        for t, c in type_result:
            by_type[t] = c

        return {
            "total": total or 0,
            "by_type": by_type,
        }

    @staticmethod
    async def generate_summary(
        db: AsyncSession,
        note_id: int,
        user_id: int,
        force: bool = False
    ) -> Dict:
        """
        为笔记生成 AI 摘要（含 LLM 缓存）

        Args:
            force: 是否强制重新生成（覆盖已有摘要）
        """
        from app.services.client.ai_service import AIService
        from app.services.common.redis import redis_client

        note = await db.get(LearningNote, note_id)
        if not note or note.user_id != user_id:
            raise NotFoundError(message="笔记不存在")

        # 空笔记直接返回空结果，不调用 AI
        if not note.content or not note.content.strip():
            return {"summary": "", "key_points": []}

        # 已有摘要且不强制重新生成，直接返回
        if note.summary and not force:
            return {
                "summary": note.summary,
                "key_points": json.loads(note.key_points) if note.key_points else [],
            }

# 检查 LLM 缓存（防止完全相同的笔记内容重复调用 AI）
        # 缓存键包含标题+类型+内容前缀，与 suggest_tags 的策略一致
        cache_content = f"{note.title}\n{note.note_type}\n{note.content[:2000]}"
        cached = await redis_client.get_llm_cache("note_summary", cache_content)
        if cached and not force:
            note.summary = cached.get("summary", "")[:300]
            note.key_points = json.dumps(cached.get("key_points", []), ensure_ascii=False)
            await db.commit()
            return cached

        # 调用 AI 生成摘要
        content = note.content[:3000]  # 截取前 3000 字，控制 token 用量
        messages = [
            {"role": "system", "content": NOTE_SUMMARIZE_PROMPT.format(
                title=note.title, note_type=note.note_type, content=content
            )},
        ]

        try:
            result = await AIService._chat(messages, temperature=0.3)
            parsed = AIService._extract_json(result)

            summary = (parsed.get("summary") or "")[:300]
            key_points = parsed.get("key_points") or []

            # 保存到数据库
            note.summary = summary
            note.key_points = json.dumps(key_points, ensure_ascii=False)
            await db.commit()

# 写入 LLM 缓存（TTL 7 天，笔记内容不变时无需重新生成）
            # 缓存键使用与读取时一致的 cache_content（含标题+类型+内容前缀）
            await redis_client.set_llm_cache(
                "note_summary", cache_content,
                {"summary": summary, "key_points": key_points},
                ttl=7 * 24 * 3600
            )

            return {"summary": summary, "key_points": key_points}
        except Exception as e:
            logger.error(f"笔记摘要生成失败: note_id={note_id}, {e}")
            return {"summary": "", "key_points": [], "error": str(e)}

    @staticmethod
    async def suggest_tags(
        db: AsyncSession,
        note_id: int,
        user_id: int,
        force: bool = False
    ) -> Dict:
        """
        为笔记推荐 AI 标签（自动分析内容）

        Args:
            force: 是否强制重新生成（忽略 LLM 缓存）
        """
        from app.services.client.ai_service import AIService
        from app.services.common.redis import redis_client

        note = await db.get(LearningNote, note_id)
        if not note or note.user_id != user_id:
            raise NotFoundError(message="笔记不存在")

        # 空笔记直接返回空结果，不调用 AI
        if not note.content or not note.content.strip():
            return {"tags": [], "reason": ""}

        # 检查 LLM 缓存（相同内容不重复调用 AI）
        cache_content = f"{note.title}\n{note.note_type}\n{note.content[:2000]}"
        try:
            cached = await redis_client.get_llm_cache("note_tags", cache_content)
        except Exception as e:
            logger.warning("读取笔记标签缓存失败: note_id=%s, %s", note_id, e)
            cached = None
        if cached and not force:
            return cached

        # 调用 AI 生成标签
        content = note.content[:2000]  # 截取前 2000 字，控制 token 用量
        messages = [
            {"role": "system", "content": NOTE_TAG_SUGGEST_PROMPT.format(
                title=note.title, note_type=note.note_type, content=content
            )},
        ]

        try:
            result = await AIService._chat(messages, temperature=0.3)
            parsed = AIService._extract_json(result)

            raw_tags = parsed.get("tags", []) or []
            reason = parsed.get("reason", "")

            # 标准化标签：别名归一 + 去重，最多保留 5 个
            tags = list(dict.fromkeys(
                normalize_tag(t) for t in raw_tags if t and t.strip()
            ))[:5]

            result_data = {"tags": tags, "reason": reason}

            # 写入 LLM 缓存（TTL 7 天，笔记内容不变时无需重新生成）
            try:
                await redis_client.set_llm_cache(
                    "note_tags", cache_content, result_data,
                    ttl=7 * 24 * 3600
                )
            except Exception as e:
                logger.warning("写入笔记标签缓存失败: note_id=%s, %s", note_id, e)

            return result_data
        except Exception as e:
            logger.error(f"笔记标签推荐失败: note_id={note_id}, {e}")
            return {"tags": [], "reason": "暂时无法生成标签，请稍后重试"}


learning_note_service = LearningNoteService()
