import json
import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience, ExperienceTag
from app.models.interview import Interview
from app.models.learning_note import LearningNote
from app.models.weakness_stat import WeaknessStat

logger = logging.getLogger(__name__)


class WeaknessService:
    @staticmethod
    def _parse_report(value) -> Dict:
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _clean_keywords(values) -> list[str]:
        cleaned = []
        for value in values or []:
            keyword = str(value).strip()
            if keyword and keyword not in cleaned:
                cleaned.append(keyword[:100])
        return cleaned

    @staticmethod
    async def record_from_interview(db: AsyncSession, user_id: int, interview_id: int) -> None:
        interview = await db.get(Interview, interview_id)
        if not interview or interview.user_id != user_id:
            return

        report = WeaknessService._parse_report(interview.report)
        keywords = WeaknessService._clean_keywords(report.get("weaknesses", []))
        if not keywords:
            return

        now = datetime.utcnow()
        avg_score = float(interview.overall_score) if interview.overall_score is not None else None
        for keyword in keywords:
            result = await db.execute(
                select(WeaknessStat).where(
                    WeaknessStat.user_id == user_id,
                    WeaknessStat.keyword == keyword,
                )
            )
            stat = result.scalar_one_or_none()
            if stat:
                old_count = stat.count or 0
                stat.count = old_count + 1
                if avg_score is not None:
                    stat.avg_score = (
                        ((stat.avg_score or avg_score) * old_count + avg_score)
                        / max(stat.count, 1)
                    )
                stat.last_occurred_at = now
            else:
                db.add(WeaknessStat(
                    user_id=user_id,
                    keyword=keyword,
                    count=1,
                    avg_score=avg_score,
                    last_occurred_at=now,
                ))

        await db.commit()

    @staticmethod
    async def get_weakness_heatmap(db: AsyncSession, user_id: int, limit: int = 30) -> Dict:
        result = await db.execute(
            select(WeaknessStat)
            .where(WeaknessStat.user_id == user_id)
            .order_by(WeaknessStat.count.desc(), WeaknessStat.last_occurred_at.desc())
            .limit(limit)
        )
        stats = result.scalars().all()
        max_count = max([item.count or 0 for item in stats], default=1)
        items = [{
            "keyword": item.keyword,
            "count": item.count or 0,
            "avg_score": round(item.avg_score, 1) if item.avg_score is not None else None,
            "last_occurred_at": item.last_occurred_at.isoformat() if item.last_occurred_at else None,
            "heat": round((item.count or 0) / max_count, 2),
        } for item in stats]
        return {"items": items, "total": len(items), "top_3": items[:3]}

    @staticmethod
    async def get_mistake_dashboard(db: AsyncSession, user_id: int) -> Dict:
        total_mistakes = await db.scalar(
            select(func.count()).select_from(LearningNote).where(
                LearningNote.user_id == user_id,
                LearningNote.note_type == "mistake",
            )
        ) or 0
        result = await db.execute(
            select(LearningNote)
            .where(
                LearningNote.user_id == user_id,
                LearningNote.note_type == "mistake",
            )
            .order_by(LearningNote.updated_at.desc())
            .limit(10)
        )
        notes = result.scalars().all()
        heatmap = await WeaknessService.get_weakness_heatmap(db, user_id)
        return {
            "mistake_count": total_mistakes,
            "recent_mistakes": [{
                "id": note.id,
                "title": note.title,
                "tags": note.tags,
                "summary": note.summary,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            } for note in notes],
            "weakness": heatmap,
        }

    @staticmethod
    async def get_recommended_practice(
        db: AsyncSession,
        user_id: int,
        limit: int = 5,
    ) -> List[Dict]:
        result = await db.execute(
            select(WeaknessStat)
            .where(WeaknessStat.user_id == user_id)
            .order_by(WeaknessStat.count.desc(), WeaknessStat.last_occurred_at.desc())
            .limit(limit)
        )
        weaknesses = result.scalars().all()
        recommendations = []
        for weakness in weaknesses:
            tag_subquery = select(ExperienceTag.experience_id).where(
                ExperienceTag.tag.ilike(f"%{weakness.keyword}%")
            )
            exp_result = await db.execute(
                select(Experience)
                .where(
                    Experience.status == "published",
                    or_(
                        Experience.title.ilike(f"%{weakness.keyword}%"),
                        Experience.content.ilike(f"%{weakness.keyword}%"),
                        Experience.company.ilike(f"%{weakness.keyword}%"),
                        Experience.position.ilike(f"%{weakness.keyword}%"),
                        Experience.id.in_(tag_subquery),
                    ),
                )
                .order_by(Experience.like_count.desc(), Experience.view_count.desc())
                .limit(3)
            )
            experiences = exp_result.scalars().all()
            recommendations.append({
                "keyword": weakness.keyword,
                "count": weakness.count or 0,
                "experiences": [{
                    "id": exp.id,
                    "title": exp.title,
                    "company": exp.company,
                    "position": exp.position,
                    "summary": exp.summary,
                } for exp in experiences],
            })
        return recommendations


weakness_service = WeaknessService()
