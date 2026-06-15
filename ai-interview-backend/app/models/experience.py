from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


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
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
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
