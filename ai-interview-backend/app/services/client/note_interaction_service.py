import logging
from math import ceil
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.exceptions.http_exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.learning_note import LearningNote
from app.models.note_interaction import (
    PublicNoteCollection,
    PublicNoteComment,
    PublicNoteLike,
)
from app.services.client.notification_service import notification_service

logger = logging.getLogger(__name__)


class NoteInteractionService:
    @staticmethod
    def _is_public(note: LearningNote) -> bool:
        return note.visibility == "public" and note.status == "published"

    @staticmethod
    def _user_payload(user) -> Dict:
        return {
            "id": user.id,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "avatar": user.avatar,
        }

    @staticmethod
    async def _get_public_note(db: AsyncSession, note_id: int) -> LearningNote:
        note = await db.get(LearningNote, note_id)
        if not note or not NoteInteractionService._is_public(note):
            raise NotFoundError(message="公开笔记不存在")
        return note

    @staticmethod
    async def toggle_like(db: AsyncSession, note_id: int, user_id: int) -> Dict:
        note = await NoteInteractionService._get_public_note(db, note_id)
        result = await db.execute(
            select(PublicNoteLike).where(
                PublicNoteLike.note_id == note_id,
                PublicNoteLike.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            note.like_count = max(0, (note.like_count or 0) - 1)
            liked = False
        else:
            db.add(PublicNoteLike(note_id=note_id, user_id=user_id))
            note.like_count = (note.like_count or 0) + 1
            liked = True
            if note.user_id != user_id:
                await notification_service.create_notification(
                    db=db,
                    user_id=note.user_id,
                    title="有人点赞了你的公开笔记",
                    content=f"你的笔记《{note.title}》收到了新的点赞",
                    notification_type="note_interaction",
                    related_id=note.id,
                    related_type="learning_note",
                    commit=False,
                )

        await db.commit()
        return {"liked": liked, "like_count": note.like_count or 0}

    @staticmethod
    async def toggle_collect(db: AsyncSession, note_id: int, user_id: int) -> Dict:
        note = await NoteInteractionService._get_public_note(db, note_id)
        result = await db.execute(
            select(PublicNoteCollection).where(
                PublicNoteCollection.note_id == note_id,
                PublicNoteCollection.user_id == user_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            note.collect_count = max(0, (note.collect_count or 0) - 1)
            collected = False
        else:
            db.add(PublicNoteCollection(note_id=note_id, user_id=user_id))
            note.collect_count = (note.collect_count or 0) + 1
            collected = True
            if note.user_id != user_id:
                await notification_service.create_notification(
                    db=db,
                    user_id=note.user_id,
                    title="有人收藏了你的公开笔记",
                    content=f"你的笔记《{note.title}》被收藏了",
                    notification_type="note_interaction",
                    related_id=note.id,
                    related_type="learning_note",
                    commit=False,
                )

        await db.commit()
        return {"collected": collected, "collect_count": note.collect_count or 0}

    @staticmethod
    async def get_interaction_status(db: AsyncSession, note_id: int, user_id: int) -> Dict:
        await NoteInteractionService._get_public_note(db, note_id)
        liked = await db.scalar(
            select(func.count()).select_from(PublicNoteLike).where(
                PublicNoteLike.note_id == note_id,
                PublicNoteLike.user_id == user_id,
            )
        )
        collected = await db.scalar(
            select(func.count()).select_from(PublicNoteCollection).where(
                PublicNoteCollection.note_id == note_id,
                PublicNoteCollection.user_id == user_id,
            )
        )
        return {"liked": bool(liked), "collected": bool(collected)}

    @staticmethod
    async def get_comments(
        db: AsyncSession,
        note_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        await NoteInteractionService._get_public_note(db, note_id)
        base = select(PublicNoteComment).where(
            PublicNoteComment.note_id == note_id,
            PublicNoteComment.parent_id.is_(None),
        )
        total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
        query = (
            base.options(joinedload(PublicNoteComment.author))
            .order_by(PublicNoteComment.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await db.execute(query)
        comments = result.unique().scalars().all()

        comment_ids = [comment.id for comment in comments]
        replies_map: dict[int, list[PublicNoteComment]] = {}
        if comment_ids:
            replies_result = await db.execute(
                select(PublicNoteComment)
                .where(PublicNoteComment.parent_id.in_(comment_ids))
                .options(joinedload(PublicNoteComment.author))
                .order_by(PublicNoteComment.created_at.asc())
            )
            for reply in replies_result.unique().scalars().all():
                replies_map.setdefault(reply.parent_id, []).append(reply)

        items = []
        for comment in comments:
            replies = [
                {
                    "id": reply.id,
                    "content": reply.content,
                    "parent_id": reply.parent_id,
                    "like_count": reply.like_count or 0,
                    "user": NoteInteractionService._user_payload(reply.author),
                    "created_at": reply.created_at.isoformat() if reply.created_at else None,
                }
                for reply in replies_map.get(comment.id, [])
            ]
            items.append({
                "id": comment.id,
                "content": comment.content,
                "parent_id": None,
                "like_count": comment.like_count or 0,
                "user": NoteInteractionService._user_payload(comment.author),
                "replies": replies,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": size,
            "last_page": ceil(total / size) if size > 0 else 0,
        }

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        note_id: int,
        user_id: int,
        content: str,
        parent_id: Optional[int] = None,
    ) -> Dict:
        note = await NoteInteractionService._get_public_note(db, note_id)
        content = (content or "").strip()
        if not content:
            raise ValidationError(message="评论内容不能为空")
        if len(content) > 500:
            raise ValidationError(message="评论内容不能超过 500 字")

        if parent_id:
            parent = await db.get(PublicNoteComment, parent_id)
            if not parent or parent.note_id != note_id:
                raise NotFoundError(message="父评论不存在")

        comment = PublicNoteComment(
            note_id=note_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content,
        )
        db.add(comment)
        note.comment_count = (note.comment_count or 0) + 1

        if note.user_id != user_id:
            await notification_service.create_notification(
                db=db,
                user_id=note.user_id,
                title="你的公开笔记有新评论",
                content=f"你的笔记《{note.title}》收到了新的评论",
                notification_type="note_interaction",
                related_id=note.id,
                related_type="learning_note",
                commit=False,
            )

        await db.commit()
        result = await db.execute(
            select(PublicNoteComment)
            .where(PublicNoteComment.id == comment.id)
            .options(joinedload(PublicNoteComment.author))
        )
        saved = result.unique().scalar_one()
        return {
            "id": saved.id,
            "content": saved.content,
            "parent_id": saved.parent_id,
            "like_count": saved.like_count or 0,
            "user": NoteInteractionService._user_payload(saved.author),
            "created_at": saved.created_at.isoformat() if saved.created_at else None,
        }

    @staticmethod
    async def delete_comment(db: AsyncSession, comment_id: int, user_id: int) -> None:
        comment = await db.get(PublicNoteComment, comment_id)
        if not comment:
            raise NotFoundError(message="评论不存在")
        if comment.user_id != user_id:
            raise AuthorizationError(message="只能删除自己的评论")

        note = await db.get(LearningNote, comment.note_id)
        if note:
            note.comment_count = max(0, (note.comment_count or 0) - 1)
        await db.delete(comment)
        await db.commit()


note_interaction_service = NoteInteractionService()
