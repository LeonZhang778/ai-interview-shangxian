from typing import Dict, Iterable, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.http_exceptions import NotFoundError
from app.models.learning_note import LearningNote


class NoteRecommendService:
    @staticmethod
    def _split_tags(value: Optional[str]) -> list[str]:
        if not value:
            return []
        return [tag.strip() for tag in value.split(",") if tag and tag.strip()]

    @staticmethod
    def _jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
        left_set = {tag.lower() for tag in left if tag}
        right_set = {tag.lower() for tag in right if tag}
        if not left_set or not right_set:
            return 0.0
        return len(left_set & right_set) / len(left_set | right_set)

    @staticmethod
    def _item(note: LearningNote, score: float = 0.0) -> Dict:
        return {
            "id": note.id,
            "title": note.title,
            "note_type": note.note_type,
            "tags": note.tags,
            "summary": note.summary,
            "visibility": note.visibility,
            "status": note.status,
            "similarity": round(score, 3),
            "created_at": note.created_at.isoformat() if note.created_at else None,
        }

    @staticmethod
    async def get_related_notes(
        db: AsyncSession,
        note_id: int,
        user_id: Optional[int] = None,
        limit: int = 5,
    ) -> Dict:
        note = await db.get(LearningNote, note_id)
        if not note:
            raise NotFoundError(message="笔记不存在")

        is_owner = bool(user_id and note.user_id == user_id)
        is_public = note.visibility == "public" and note.status == "published"
        if not is_owner and not is_public:
            raise NotFoundError(message="笔记不存在")

        tags = NoteRecommendService._split_tags(note.tags)
        conditions = [LearningNote.id != note_id]
        if user_id:
            conditions.append(or_(
                LearningNote.user_id == user_id,
                and_(
                    LearningNote.visibility == "public",
                    LearningNote.status == "published",
                ),
            ))
        else:
            conditions.extend([
                LearningNote.visibility == "public",
                LearningNote.status == "published",
            ])

        if tags:
            tag_filters = []
            for tag in tags:
                tag_filters.extend([
                    LearningNote.tags == tag,
                    LearningNote.tags.ilike(f"{tag},%"),
                    LearningNote.tags.ilike(f"%,{tag}"),
                    LearningNote.tags.ilike(f"%,{tag},%"),
                ])
            conditions.append(or_(*tag_filters))
        else:
            title_keyword = note.title[:20]
            conditions.append(or_(
                LearningNote.note_type == note.note_type,
                LearningNote.title.ilike(f"%{title_keyword}%"),
            ))

        result = await db.execute(
            select(LearningNote)
            .where(*conditions)
            .order_by(LearningNote.updated_at.desc())
            .limit(max(limit * 4, limit))
        )
        candidates = result.scalars().all()

        scored = []
        for candidate in candidates:
            candidate_tags = NoteRecommendService._split_tags(candidate.tags)
            score = NoteRecommendService._jaccard_similarity(tags, candidate_tags)
            if candidate.note_type == note.note_type:
                score += 0.1
            if not tags and candidate.note_type == note.note_type:
                score += 0.2
            if score > 0:
                scored.append((score, candidate))

        scored.sort(
            key=lambda item: (
                -item[0],
                -((item[1].updated_at or item[1].created_at).timestamp()
                  if (item[1].updated_at or item[1].created_at) else 0),
            )
        )
        items = [
            NoteRecommendService._item(candidate, score)
            for score, candidate in scored[:limit]
        ]
        return {"items": items, "total": len(items)}

    @staticmethod
    async def recommend_for_interview(
        db: AsyncSession,
        user_id: int,
        keywords: list[str],
        limit: int = 5,
    ) -> Dict:
        cleaned = [kw.strip() for kw in keywords if kw and kw.strip()]
        if not cleaned:
            return {"items": [], "total": 0}

        filters = []
        for keyword in cleaned[:10]:
            filters.extend([
                LearningNote.title.ilike(f"%{keyword}%"),
                LearningNote.tags.ilike(f"%{keyword}%"),
                LearningNote.content.ilike(f"%{keyword}%"),
            ])

        result = await db.execute(
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                or_(*filters),
            )
            .order_by(LearningNote.updated_at.desc())
            .limit(limit)
        )
        notes = result.scalars().all()
        items = [NoteRecommendService._item(note) for note in notes]
        return {"items": items, "total": len(items)}


note_recommend_service = NoteRecommendService()
