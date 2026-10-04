from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class CollectionGroup(BaseModel):
    __tablename__ = "collection_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")

    collections = relationship("UserCollection", back_populates="group")


class Experience(BaseModel):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    company = Column(String(50), nullable=False, index=True)
    position = Column(String(50), nullable=False, index=True)
    level = Column(String(20), nullable=True)  # 校招/1-3年/3-5年/5年+
    round = Column(String(20), nullable=True)  # 一面/二面/三面/HR面/综合
    content = Column(Text, nullable=False)
    summary = Column(String(500), nullable=True)
    # 计数列统一为 NOT NULL DEFAULT 0：
    # 此前只写了 Python 层 default（无 server_default、列可空），而线上这张表是手工 SQL
    # 建的、带 DEFAULT 0 —— 两边形状不一致。于是任何绕过 ORM 的 INSERT 在开发库得到 NULL，
    # 在线上得到 0；读取路径也就必须靠 COALESCE 兜底。把约束写进模型才是根治，
    # 见迁移 p8b9c0d1e2f3（把已有库幂等对齐到同一形状）。
    view_count = Column(Integer, nullable=False, default=0, server_default="0")
    like_count = Column(Integer, nullable=False, default=0, server_default="0")
    collect_count = Column(Integer, nullable=False, default=0, server_default="0")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_anonymous = Column(Boolean, default=True)
    status = Column(String(20), default="published")  # draft/published

    # 关联关系
    author = relationship("User", backref="experiences")
    tags = relationship("ExperienceTag", back_populates="experience", cascade="all, delete-orphan")


class ExperienceTag(BaseModel):
    __tablename__ = "experience_tags"

    experience_id = Column(Integer, ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True)
    tag = Column(String(30), primary_key=True)

    experience = relationship("Experience", back_populates="tags")


class UserCollection(BaseModel):
    __tablename__ = "user_collections"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    experience_id = Column(Integer, ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True)
    group_id = Column(Integer, ForeignKey("collection_groups.id", ondelete="SET NULL"), nullable=True, index=True)

    group = relationship("CollectionGroup", back_populates="collections")
    experience = relationship("Experience", backref="collections")


class UserLike(BaseModel):
    __tablename__ = "user_likes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    experience_id = Column(Integer, ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "experience_id", name="uq_user_like"),
    )


class ExperienceComment(BaseModel):
    __tablename__ = "experience_comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    experience_id = Column(Integer, ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("experience_comments.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    like_count = Column(Integer, nullable=False, default=0, server_default="0")

    author = relationship("User", lazy="joined")
    replies = relationship("ExperienceComment", backref="parent", remote_side="ExperienceComment.id", lazy="selectin")
