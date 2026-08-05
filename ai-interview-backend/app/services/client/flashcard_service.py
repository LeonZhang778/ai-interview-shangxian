import logging
from datetime import datetime, timedelta
from math import ceil
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.http_exceptions import NotFoundError, ValidationError
from app.models.flashcard import Flashcard
from app.models.learning_note import LearningNote

logger = logging.getLogger(__name__)


class SM2Algorithm:
    @staticmethod
    def calculate(quality: int, ease_factor: float, interval: int, repetitions: int) -> Dict:
        if quality < 0 or quality > 5:
            raise ValidationError(message="评分必须在 0-5 之间")

        if quality < 3:
            repetitions = 0
            interval = 1
        else:
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = round(interval * ease_factor)
            repetitions += 1

        ease_factor = max(
            1.3,
            ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )
        interval = min(interval, 365)
        return {
            "ease_factor": round(ease_factor, 2),
            "interval": interval,
            "repetitions": repetitions,
            "next_review_at": datetime.utcnow() + timedelta(days=interval),
        }


class FlashcardService:
    @staticmethod
    def _item(card: Flashcard) -> Dict:
        return {
            "id": card.id,
            "note_id": card.note_id,
            "question": card.question,
            "answer": card.answer,
            "source": card.source,
            "ease_factor": card.ease_factor,
            "interval": card.interval,
            "repetitions": card.repetitions,
            "next_review_at": card.next_review_at.isoformat() if card.next_review_at else None,
            "last_reviewed_at": card.last_reviewed_at.isoformat() if card.last_reviewed_at else None,
            "last_quality": card.last_quality,
        }

    @staticmethod
    async def get_due_cards(db: AsyncSession, user_id: int, limit: int = 20) -> Dict:
        now = datetime.utcnow()
        result = await db.execute(
            select(Flashcard)
            .where(Flashcard.user_id == user_id, Flashcard.next_review_at <= now)
            .order_by(Flashcard.next_review_at.asc())
            .limit(limit)
        )
        cards = result.scalars().all()
        return {"cards": [FlashcardService._item(card) for card in cards], "count": len(cards)}

    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> Dict:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        total = await db.scalar(
            select(func.count()).select_from(Flashcard).where(Flashcard.user_id == user_id)
        ) or 0
        due = await db.scalar(
            select(func.count()).select_from(Flashcard).where(
                Flashcard.user_id == user_id,
                Flashcard.next_review_at <= now,
            )
        ) or 0
        mastered = await db.scalar(
            select(func.count()).select_from(Flashcard).where(
                Flashcard.user_id == user_id,
                Flashcard.interval >= 21,
            )
        ) or 0
        reviewed_today = await db.scalar(
            select(func.count()).select_from(Flashcard).where(
                Flashcard.user_id == user_id,
                Flashcard.last_reviewed_at >= today_start,
            )
        ) or 0
        return {
            "total": total,
            "due": due,
            "mastered": mastered,
            "reviewed_today": reviewed_today,
        }

    @staticmethod
    async def review_card(db: AsyncSession, user_id: int, card_id: int, quality: int) -> Dict:
        card = await db.get(Flashcard, card_id)
        if not card or card.user_id != user_id:
            raise NotFoundError(message="闪卡不存在")

        result = SM2Algorithm.calculate(
            quality=quality,
            ease_factor=card.ease_factor or 2.5,
            interval=card.interval or 0,
            repetitions=card.repetitions or 0,
        )
        card.ease_factor = result["ease_factor"]
        card.interval = result["interval"]
        card.repetitions = result["repetitions"]
        card.next_review_at = result["next_review_at"]
        card.last_reviewed_at = datetime.utcnow()
        card.last_quality = quality
        await db.commit()
        return {
            "id": card.id,
            "quality": quality,
            "next_review_at": result["next_review_at"].isoformat(),
            "interval_days": result["interval"],
            "ease_factor": result["ease_factor"],
            "repetitions": result["repetitions"],
        }

    @staticmethod
    async def generate_from_note(db: AsyncSession, user_id: int, note_id: int) -> Dict:
        note = await db.get(LearningNote, note_id)
        if not note or note.user_id != user_id:
            raise NotFoundError(message="笔记不存在")
        if not note.content or not note.content.strip():
            raise ValidationError(message="空笔记无法生成闪卡")

        existing = await db.scalar(
            select(func.count()).select_from(Flashcard).where(
                Flashcard.user_id == user_id,
                Flashcard.note_id == note_id,
                Flashcard.source == "auto",
            )
        )
        if existing:
            return {"message": "该笔记已生成过闪卡", "cards": []}

        from app.prompts.learning_note import FLASHCARD_GENERATE_PROMPT
        from app.services.client.ai_service import AIService

        messages = [{
            "role": "system",
            "content": FLASHCARD_GENERATE_PROMPT.format(
                title=note.title,
                content=note.content[:3000],
            ),
        }]
        try:
            result = await AIService._chat(messages, temperature=0.3)
            parsed = AIService._extract_json(result)
            pairs = parsed.get("cards", []) or []
        except Exception as exc:
            logger.error("闪卡生成失败: note_id=%s, %s", note_id, exc)
            return {"message": "暂时无法生成闪卡，请稍后重试", "cards": []}

        cards: List[Flashcard] = []
        for pair in pairs[:10]:
            question = (pair.get("question") or "").strip()
            answer = (pair.get("answer") or "").strip()
            if not question or not answer:
                continue
            card = Flashcard(
                user_id=user_id,
                note_id=note_id,
                question=question[:500],
                answer=answer,
                source="auto",
            )
            db.add(card)
            cards.append(card)

        if not cards:
            return {"message": "未提取到可复习的闪卡", "cards": []}

        await db.commit()
        for card in cards:
            await db.refresh(card)
        return {
            "message": f"已生成 {len(cards)} 张闪卡",
            "cards": [{"id": card.id, "question": card.question} for card in cards],
        }

    @staticmethod
    async def list_cards(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        query = select(Flashcard).where(Flashcard.user_id == user_id).order_by(Flashcard.created_at.desc())
        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        result = await db.execute(query.offset((page - 1) * size).limit(size))
        cards = result.scalars().all()
        return {
            "items": [FlashcardService._item(card) for card in cards],
            "total": total,
            "page": page,
            "per_page": size,
            "last_page": ceil(total / size) if size > 0 else 0,
        }


flashcard_service = FlashcardService()
