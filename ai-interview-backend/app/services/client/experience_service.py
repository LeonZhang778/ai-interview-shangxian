import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload
from app.models.experience import Experience, ExperienceTag, UserCollection, UserLike, ExperienceComment
from app.models.user import User
from app.exceptions.http_exceptions import NotFoundError

logger = logging.getLogger(__name__)


class ExperienceService:

    @staticmethod
    async def get_experiences(
        db: AsyncSession,
        company: Optional[str] = None,
        position: Optional[str] = None,
        level: Optional[str] = None,
        round_: Optional[str] = None,
        sort: str = "latest",
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """获取面经列表，支持筛选和分页"""
        query = select(Experience).where(Experience.status == "published")

        if company:
            query = query.where(Experience.company == company)
        if position:
            query = query.where(Experience.position == position)
        if level:
            query = query.where(Experience.level == level)
        if round_:
            query = query.where(Experience.round == round_)

        # 排序
        if sort == "popular":
            query = query.order_by(Experience.view_count.desc())
        elif sort == "collected":
            query = query.order_by(Experience.collect_count.desc())
        else:
            query = query.order_by(Experience.created_at.desc())

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await db.execute(query)
        experiences = result.scalars().all()

        # 批量获取标签
        exp_ids = [e.id for e in experiences]
        tags_map = {}
        if exp_ids:
            tag_query = select(ExperienceTag).where(ExperienceTag.experience_id.in_(exp_ids))
            tag_result = await db.execute(tag_query)
            for t in tag_result.scalars().all():
                tags_map.setdefault(t.experience_id, []).append(t.tag)

        items = [
            {
                "id": e.id,
                "title": e.title,
                "company": e.company,
                "position": e.position,
                "level": e.level,
                "round": e.round,
                "summary": e.summary,
                "view_count": e.view_count,
                "like_count": e.like_count,
                "collect_count": e.collect_count,
                "tags": tags_map.get(e.id, []),
                "created_at": e.created_at.strftime("%Y-%m-%d") if e.created_at else None
            }
            for e in experiences
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "has_more": (page * size) < total
        }

    @staticmethod
    async def get_experience_detail(
        db: AsyncSession,
        experience_id: int,
        user_id: Optional[int] = None
    ) -> Dict:
        """获取面经详情，同时增加阅读量"""
        query = select(Experience).where(
            Experience.id == experience_id,
            Experience.status == "published"
        ).options(selectinload(Experience.tags))
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise NotFoundError(message="面经不存在")

        # 增加阅读量
        experience.view_count += 1
        await db.commit()

        # 获取作者信息
        author_name = "匿名用户"
        if not experience.is_anonymous and experience.author_id:
            from app.models.user import User
            user_query = select(User).where(User.id == experience.author_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            if user:
                author_name = user.first_name or user.email.split("@")[0]

        # 获取相关面经（同公司或同岗位的其他文章）
        related_query = select(Experience).where(
            Experience.id != experience_id,
            Experience.status == "published"
        )
        # 优先同公司，其次同岗位
        related_query = related_query.where(
            (Experience.company == experience.company) | (Experience.position == experience.position)
        ).order_by(Experience.view_count.desc()).limit(3)

        related_result = await db.execute(related_query)
        related_experiences = related_result.scalars().all()

        # 获取相关面经的标签
        related_ids = [r.id for r in related_experiences]
        related_tags_map = {}
        if related_ids:
            tag_query = select(ExperienceTag).where(ExperienceTag.experience_id.in_(related_ids))
            tag_result = await db.execute(tag_query)
            for t in tag_result.scalars().all():
                related_tags_map.setdefault(t.experience_id, []).append(t.tag)

        related_items = [
            {
                "id": r.id,
                "title": r.title,
                "company": r.company,
                "position": r.position,
                "level": r.level,
                "round": r.round,
                "summary": r.summary,
                "view_count": r.view_count,
                "like_count": r.like_count,
                "collect_count": r.collect_count,
                "tags": related_tags_map.get(r.id, []),
                "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else None
            }
            for r in related_experiences
        ]

        # 获取标签
        tags = [t.tag for t in experience.tags]

        return {
            "id": experience.id,
            "title": experience.title,
            "company": experience.company,
            "position": experience.position,
            "level": experience.level,
            "round": experience.round,
            "content": experience.content,
            "summary": experience.summary,
            "view_count": experience.view_count,
            "like_count": experience.like_count,
            "collect_count": experience.collect_count,
            "is_anonymous": experience.is_anonymous,
            "author_name": author_name,
            "tags": tags,
            "related": related_items,
            "created_at": experience.created_at.strftime("%Y-%m-%d") if experience.created_at else None
        }

    @staticmethod
    async def like_experience(
        db: AsyncSession,
        experience_id: int,
        user_id: int
    ) -> Dict:
        """点赞/取消点赞面经（toggle）"""
        experience = await db.get(Experience, experience_id)
        if not experience or experience.status != "published":
            raise NotFoundError(message="面经不存在")

        result = await db.execute(
            select(UserLike).where(
                UserLike.user_id == user_id,
                UserLike.experience_id == experience_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await db.delete(existing)
            experience.like_count = max(0, experience.like_count - 1)
            liked = False
        else:
            db.add(UserLike(user_id=user_id, experience_id=experience_id))
            experience.like_count += 1
            liked = True

        await db.commit()
        return {"liked": liked, "like_count": experience.like_count}

    @staticmethod
    async def collect_experience(
        db: AsyncSession,
        experience_id: int,
        user_id: int
    ) -> Dict:
        """收藏/取消收藏面经"""
        experience = await db.get(Experience, experience_id)
        if not experience or experience.status != "published":
            raise NotFoundError(message="面经不存在")

        # 检查是否已收藏
        query = select(UserCollection).where(
            UserCollection.user_id == user_id,
            UserCollection.experience_id == experience_id
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # 取消收藏
            await db.delete(existing)
            experience.collect_count = max(0, experience.collect_count - 1)
            collected = False
        else:
            # 添加收藏
            collection = UserCollection(user_id=user_id, experience_id=experience_id)
            db.add(collection)
            experience.collect_count += 1
            collected = True

        await db.commit()

        return {
            "collected": collected,
            "collect_count": experience.collect_count
        }

    @staticmethod
    async def get_comments(
        db: AsyncSession,
        experience_id: int,
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """获取评论列表（顶级评论 + 嵌套回复）"""
        # 只查顶级评论
        query = (
            select(ExperienceComment)
            .where(
                ExperienceComment.experience_id == experience_id,
                ExperienceComment.parent_id.is_(None)
            )
            .options(joinedload(ExperienceComment.author))
            .order_by(ExperienceComment.created_at.desc())
        )
        count_query = select(func.count()).select_from(
            select(ExperienceComment).where(
                ExperienceComment.experience_id == experience_id,
                ExperienceComment.parent_id.is_(None)
            ).subquery()
        )
        total = await db.scalar(count_query)

        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        comments = result.unique().scalars().all()

        # 批量查回复
        comment_ids = [c.id for c in comments]
        replies_map = {}
        if comment_ids:
            reply_query = (
                select(ExperienceComment)
                .where(
                    ExperienceComment.parent_id.in_(comment_ids)
                )
                .options(joinedload(ExperienceComment.author))
                .order_by(ExperienceComment.created_at.asc())
            )
            reply_result = await db.execute(reply_query)
            for r in reply_result.unique().scalars().all():
                replies_map.setdefault(r.parent_id, []).append(r)

        items = []
        for c in comments:
            replies_data = []
            for r in replies_map.get(c.id, []):
                replies_data.append({
                    "id": r.id,
                    "content": r.content,
                    "user": {"id": r.author.id, "first_name": r.author.first_name or "", "avatar": r.author.avatar},
                    "parent_id": r.parent_id,
                    "like_count": r.like_count,
                    "created_at": r.created_at.isoformat(),
                })
            items.append({
                "id": c.id,
                "content": c.content,
                "user": {"id": c.author.id, "first_name": c.author.first_name or "", "avatar": c.author.avatar},
                "parent_id": None,
                "replies": replies_data,
                "like_count": c.like_count,
                "created_at": c.created_at.isoformat(),
            })

        return {"items": items, "total": total, "page": page, "per_page": size}

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        experience_id: int,
        user_id: int,
        content: str,
        parent_id: Optional[int] = None
    ) -> Dict:
        """发表评论"""
        experience = await db.get(Experience, experience_id)
        if not experience or experience.status != "published":
            raise NotFoundError(message="面经不存在")

        if parent_id:
            parent = await db.get(ExperienceComment, parent_id)
            if not parent or parent.experience_id != experience_id:
                raise NotFoundError(message="父评论不存在")

        comment = ExperienceComment(
            experience_id=experience_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        return {
            "id": comment.id,
            "content": comment.content,
            "user": {"id": comment.author.id, "first_name": comment.author.first_name or "", "avatar": comment.author.avatar},
            "parent_id": comment.parent_id,
            "like_count": 0,
            "created_at": comment.created_at.isoformat(),
        }

    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: int,
        user_id: int
    ) -> None:
        """删除自己的评论"""
        comment = await db.get(ExperienceComment, comment_id)
        if not comment:
            raise NotFoundError(message="评论不存在")
        if comment.user_id != user_id:
            from app.exceptions.http_exceptions import AuthorizationError
            raise AuthorizationError(message="只能删除自己的评论")

        await db.delete(comment)
        await db.commit()

    @staticmethod
    async def check_user_liked(db: AsyncSession, user_id: int, experience_id: int) -> bool:
        """检查用户是否已点赞"""
        result = await db.execute(
            select(UserLike).where(
                UserLike.user_id == user_id,
                UserLike.experience_id == experience_id
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def check_user_collected(db: AsyncSession, user_id: int, experience_id: int) -> bool:
        """检查用户是否已收藏"""
        result = await db.execute(
            select(UserCollection).where(
                UserCollection.user_id == user_id,
                UserCollection.experience_id == experience_id
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_filter_options(db: AsyncSession) -> Dict:
        """获取筛选选项（所有出现过的公司、岗位、级别、轮次）"""
        companies_result = await db.execute(
            select(Experience.company).where(Experience.status == "published").distinct().order_by(Experience.company)
        )
        positions_result = await db.execute(
            select(Experience.position).where(Experience.status == "published").distinct().order_by(Experience.position)
        )
        levels_result = await db.execute(
            select(Experience.level).where(Experience.status == "published", Experience.level.isnot(None)).distinct()
        )
        rounds_result = await db.execute(
            select(Experience.round).where(Experience.status == "published", Experience.round.isnot(None)).distinct()
        )

        return {
            "companies": [r[0] for r in companies_result.fetchall()],
            "positions": [r[0] for r in positions_result.fetchall()],
            "levels": [r[0] for r in levels_result.fetchall()],
            "rounds": [r[0] for r in rounds_result.fetchall()]
        }


experience_service = ExperienceService()
