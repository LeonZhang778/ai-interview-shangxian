import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload
from app.models.experience import Experience, ExperienceTag, UserCollection, UserLike, ExperienceComment, CollectionGroup
from app.models.user import User
from app.exceptions.http_exceptions import NotFoundError, AuthorizationError

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


    @staticmethod
    async def submit_experience(
        db: AsyncSession,
        user_id: int,
        title: str,
        company: str,
        position: str,
        content: str,
        level: Optional[str] = None,
        round_: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[list] = None,
        is_anonymous: bool = False,
    ) -> Dict:
        """用户提交面经投稿"""
        experience = Experience(
            title=title,
            company=company,
            position=position,
            content=content,
            level=level,
            round=round_,
            summary=summary or content[:200],
            author_id=user_id,
            is_anonymous=is_anonymous,
            status="pending",
        )
        db.add(experience)
        await db.commit()
        await db.refresh(experience)

        # 添加标签
        if tags:
            for tag_name in tags:
                db.add(ExperienceTag(experience_id=experience.id, tag=tag_name))
            await db.commit()

        return {
            "id": experience.id,
            "title": experience.title,
            "status": experience.status,
        }

    @staticmethod
    async def get_my_experiences(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        """获取我的投稿列表"""
        query = (
            select(Experience)
            .where(Experience.author_id == user_id)
            .order_by(Experience.created_at.desc())
        )
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total = await db.scalar(count_query)

        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        experiences = result.scalars().all()

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
                "status": e.status,
                "tags": tags_map.get(e.id, []),
                "created_at": e.created_at.strftime("%Y-%m-%d") if e.created_at else None,
            }
            for e in experiences
        ]

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def get_my_experience_detail(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
    ) -> Dict:
        """获取当前用户自己的投稿详情"""
        query = (
            select(Experience)
            .where(Experience.id == experience_id)
            .options(selectinload(Experience.tags))
        )
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise NotFoundError(message="面经不存在")
        if experience.author_id != user_id:
            raise AuthorizationError(message="只能查看自己的投稿")

        return {
            "id": experience.id,
            "title": experience.title,
            "company": experience.company,
            "position": experience.position,
            "level": experience.level,
            "round": experience.round,
            "content": experience.content,
            "summary": experience.summary,
            "status": experience.status,
            "is_anonymous": experience.is_anonymous,
            "tags": [t.tag for t in experience.tags],
            "created_at": experience.created_at.strftime("%Y-%m-%d %H:%M") if experience.created_at else None,
        }

    @staticmethod
    async def update_my_experience(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
        title: str,
        company: str,
        position: str,
        content: str,
        level: Optional[str] = None,
        round_: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[list] = None,
        is_anonymous: bool = False,
    ) -> Dict:
        """更新当前用户自己的投稿，并重新置为待审核"""
        query = (
            select(Experience)
            .where(Experience.id == experience_id)
            .options(selectinload(Experience.tags))
        )
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise NotFoundError(message="面经不存在")
        if experience.author_id != user_id:
            raise AuthorizationError(message="只能修改自己的投稿")

        experience.title = title
        experience.company = company
        experience.position = position
        experience.content = content
        experience.level = level
        experience.round = round_
        experience.summary = summary or content[:200]
        experience.is_anonymous = is_anonymous
        experience.status = "pending"

        for tag in list(experience.tags):
            await db.delete(tag)
        await db.flush()

        for tag_name in tags or []:
            clean_tag = str(tag_name).strip()
            if clean_tag:
                db.add(ExperienceTag(experience_id=experience.id, tag=clean_tag))

        await db.commit()
        await db.refresh(experience)

        return {"id": experience.id, "status": experience.status}


    @staticmethod
    async def admin_list_experiences(
        db: AsyncSession,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> Dict:
        """管理员获取面经列表（含待审核）"""
        query = select(Experience).order_by(Experience.created_at.desc())
        if status:
            query = query.where(Experience.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        experiences = result.scalars().all()

        exp_ids = [e.id for e in experiences]
        tags_map = {}
        if exp_ids:
            tag_query = select(ExperienceTag).where(ExperienceTag.experience_id.in_(exp_ids))
            tag_result = await db.execute(tag_query)
            for t in tag_result.scalars().all():
                tags_map.setdefault(t.experience_id, []).append(t.tag)

        # Get author names
        author_ids = [e.author_id for e in experiences if e.author_id]
        authors_map = {}
        if author_ids:
            author_query = select(User).where(User.id.in_(author_ids))
            author_result = await db.execute(author_query)
            for u in author_result.scalars().all():
                authors_map[u.id] = u.first_name or u.email.split("@")[0]

        items = [
            {
                "id": e.id,
                "title": e.title,
                "company": e.company,
                "position": e.position,
                "status": e.status,
                "is_anonymous": e.is_anonymous,
                "author_name": authors_map.get(e.author_id, "未知") if not e.is_anonymous else "匿名",
                "tags": tags_map.get(e.id, []),
                "view_count": e.view_count,
                "like_count": e.like_count,
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M") if e.created_at else None,
            }
            for e in experiences
        ]

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def admin_review_experience(
        db: AsyncSession,
        experience_id: int,
        action: str,
    ) -> Dict:
        """管理员审核面经（approve/reject）"""
        experience = await db.get(Experience, experience_id)
        if not experience:
            raise NotFoundError(message="面经不存在")

        if action == "approve":
            experience.status = "published"
        elif action == "reject":
            experience.status = "rejected"
        else:
            from app.exceptions.http_exceptions import ValidationError
            raise ValidationError(message="无效的操作")

        await db.commit()
        return {"id": experience.id, "status": experience.status}

    @staticmethod
    async def admin_get_experience_detail(
        db: AsyncSession,
        experience_id: int,
    ) -> Dict:
        """管理员获取面经详情"""
        query = select(Experience).where(Experience.id == experience_id).options(selectinload(Experience.tags))
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise NotFoundError(message="面经不存在")

        author_name = "匿名用户"
        if not experience.is_anonymous and experience.author_id:
            user_query = select(User).where(User.id == experience.author_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            if user:
                author_name = user.first_name or user.email.split("@")[0]

        return {
            "id": experience.id,
            "title": experience.title,
            "company": experience.company,
            "position": experience.position,
            "level": experience.level,
            "round": experience.round,
            "content": experience.content,
            "summary": experience.summary,
            "status": experience.status,
            "is_anonymous": experience.is_anonymous,
            "author_name": author_name,
            "tags": [t.tag for t in experience.tags],
            "view_count": experience.view_count,
            "like_count": experience.like_count,
            "collect_count": experience.collect_count,
            "created_at": experience.created_at.strftime("%Y-%m-%d %H:%M") if experience.created_at else None,
        }

    @staticmethod
    async def admin_delete_experience(
        db: AsyncSession,
        experience_id: int,
    ) -> Dict:
        """管理员删除面经"""
        from sqlalchemy import delete as sql_delete, update as sql_update
        from app.models.interview import Interview

        experience = await db.get(Experience, experience_id)
        if not experience:
            raise NotFoundError(message="面经不存在")
        title = experience.title

        # 先清理关联的面试记录（置空 experience_id）
        await db.execute(
            sql_update(Interview).where(Interview.experience_id == experience_id).values(experience_id=None)
        )
        # 删除关联数据
        await db.execute(sql_delete(ExperienceComment).where(ExperienceComment.experience_id == experience_id))
        await db.execute(sql_delete(UserLike).where(UserLike.experience_id == experience_id))
        await db.execute(sql_delete(UserCollection).where(UserCollection.experience_id == experience_id))
        await db.execute(sql_delete(ExperienceTag).where(ExperienceTag.experience_id == experience_id))

        await db.delete(experience)
        await db.commit()
        return {"id": experience_id, "title": title}

    @staticmethod
    async def admin_batch_review(
        db: AsyncSession,
        experience_ids: list,
        action: str,
    ) -> Dict:
        """管理员批量审核面经"""
        from sqlalchemy import delete as sql_delete, update as sql_update
        from app.models.interview import Interview

        if action not in ("approve", "reject", "delete"):
            from app.exceptions.http_exceptions import ValidationError
            raise ValidationError(message="无效的操作")

        count = 0
        for eid in experience_ids:
            experience = await db.get(Experience, eid)
            if not experience:
                continue
            if action == "delete":
                # 先清理关联的面试记录（置空 experience_id）
                await db.execute(
                    sql_update(Interview).where(Interview.experience_id == eid).values(experience_id=None)
                )
                # 删除关联数据
                await db.execute(sql_delete(ExperienceComment).where(ExperienceComment.experience_id == eid))
                await db.execute(sql_delete(UserLike).where(UserLike.experience_id == eid))
                await db.execute(sql_delete(UserCollection).where(UserCollection.experience_id == eid))
                await db.execute(sql_delete(ExperienceTag).where(ExperienceTag.experience_id == eid))
                await db.delete(experience)
            elif action == "approve":
                experience.status = "published"
            elif action == "reject":
                experience.status = "rejected"
            count += 1

        await db.commit()
        return {"affected": count, "action": action}

    # ==================== 收藏夹分组 ====================

    @staticmethod
    async def get_user_collections(
        db: AsyncSession,
        user_id: int,
        group_id: Optional[int] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict:
        """获取用户的收藏列表（可按分组筛选）"""
        from app.models.experience import CollectionGroup

        query = (
            select(UserCollection)
            .where(UserCollection.user_id == user_id)
            .options(
                joinedload(UserCollection.group),
                selectinload(UserCollection.experience).joinedload(Experience.author),
                selectinload(UserCollection.experience).selectinload(Experience.tags)
            )
        )

        if group_id is not None:
            if group_id == 0:
                query = query.where(UserCollection.group_id.is_(None))
            else:
                query = query.where(UserCollection.group_id == group_id)

        # 总数
        count_query = select(func.count()).select_from(UserCollection).where(
            UserCollection.user_id == user_id
        )
        if group_id is not None:
            if group_id == 0:
                count_query = count_query.where(UserCollection.group_id.is_(None))
            else:
                count_query = count_query.where(UserCollection.group_id == group_id)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页查询
        query = query.order_by(UserCollection.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        collections = result.scalars().unique().all()

        items = []
        for c in collections:
            exp = c.experience
            if not exp:
                continue
            items.append({
                "group_id": c.group_id,
                "group_name": c.group.name if c.group else None,
                "experience": {
                    "id": exp.id,
                    "title": exp.title,
                    "company": exp.company,
                    "position": exp.position,
                    "summary": exp.summary,
                    "view_count": exp.view_count,
                    "like_count": exp.like_count,
                    "collect_count": exp.collect_count,
                    "author_name": (exp.author.first_name or exp.author.email.split("@")[0]) if exp.author and not exp.is_anonymous else "匿名用户",
                    "tags": [t.tag for t in exp.tags] if exp.tags else [],
                    "created_at": exp.created_at.strftime("%Y-%m-%d %H:%M") if exp.created_at else None,
                }
            })

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def get_collection_groups(
        db: AsyncSession,
        user_id: int
    ) -> list:
        """获取用户的收藏分组列表"""
        from app.models.experience import CollectionGroup

        query = (
            select(CollectionGroup)
            .where(CollectionGroup.user_id == user_id)
            .order_by(CollectionGroup.sort_order, CollectionGroup.id)
        )
        result = await db.execute(query)
        groups = result.scalars().all()

        # 统计每个分组的收藏数
        items = []
        for g in groups:
            count_query = select(func.count()).select_from(UserCollection).where(
                UserCollection.user_id == user_id,
                UserCollection.group_id == g.id
            )
            count_result = await db.execute(count_query)
            count = count_result.scalar()
            items.append({
                "id": g.id,
                "name": g.name,
                "sort_order": g.sort_order,
                "count": count
            })

        # 未分组数量
        ungrouped_query = select(func.count()).select_from(UserCollection).where(
            UserCollection.user_id == user_id,
            UserCollection.group_id.is_(None)
        )
        ungrouped_result = await db.execute(ungrouped_query)
        ungrouped_count = ungrouped_result.scalar()

        return {"groups": items, "ungrouped_count": ungrouped_count}

    @staticmethod
    async def create_collection_group(
        db: AsyncSession,
        user_id: int,
        name: str
    ) -> Dict:
        """创建收藏分组"""
        from app.models.experience import CollectionGroup

        group = CollectionGroup(user_id=user_id, name=name)
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return {"id": group.id, "name": group.name, "sort_order": group.sort_order, "count": 0}

    @staticmethod
    async def update_collection_group(
        db: AsyncSession,
        user_id: int,
        group_id: int,
        name: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Dict:
        """更新收藏分组"""
        from app.models.experience import CollectionGroup

        group = await db.get(CollectionGroup, group_id)
        if not group or group.user_id != user_id:
            raise NotFoundError(message="分组不存在")

        if name is not None:
            group.name = name
        if sort_order is not None:
            group.sort_order = sort_order

        await db.commit()
        return {"id": group.id, "name": group.name, "sort_order": group.sort_order}

    @staticmethod
    async def delete_collection_group(
        db: AsyncSession,
        user_id: int,
        group_id: int
    ) -> Dict:
        """删除收藏分组（分组内的收藏项不会被删除，只是变为未分组）"""
        from app.models.experience import CollectionGroup

        group = await db.get(CollectionGroup, group_id)
        if not group or group.user_id != user_id:
            raise NotFoundError(message="分组不存在")

        # 将该分组下的收藏项设为未分组
        await db.execute(
            update(UserCollection).where(
                UserCollection.group_id == group_id
            ).values(group_id=None)
        )

        await db.delete(group)
        await db.commit()
        return {"id": group_id}

    @staticmethod
    async def move_collection(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
        group_id: Optional[int]
    ) -> Dict:
        """移动收藏到指定分组"""
        from app.models.experience import CollectionGroup

        query = select(UserCollection).where(
            UserCollection.user_id == user_id,
            UserCollection.experience_id == experience_id
        )
        result = await db.execute(query)
        collection = result.scalar_one_or_none()

        if not collection:
            raise NotFoundError(message="收藏不存在")

        if group_id is not None and group_id != 0:
            group = await db.get(CollectionGroup, group_id)
            if not group or group.user_id != user_id:
                raise NotFoundError(message="分组不存在")
            collection.group_id = group_id
        else:
            collection.group_id = None

        await db.commit()
        return {"experience_id": experience_id, "group_id": collection.group_id}


experience_service = ExperienceService()
