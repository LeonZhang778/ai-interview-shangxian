from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class LearningNote(BaseModel):
    __tablename__ = "learning_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    note_type = Column(String(20), nullable=False, default="note")
    # note_type: note(笔记) / experience(面经) / mistake(错题) / review(复盘) / material(资料)
    visibility = Column(String(20), nullable=False, default="private")
    # visibility: private(仅自己) / public(公开进广场)
    status = Column(String(20), nullable=False, default="draft")
    # status: draft(草稿) / published(已发布)
    tags = Column(String(500), nullable=True)
    # tags: 逗号分隔的标签字符串
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True, index=True)
    # 关联的 AI 面试记录（面试结果回流时填充）
    source = Column(String(20), nullable=False, default="manual")
    # source: manual(手动创建) / interview(面试回流)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

    user = relationship("User", backref="learning_notes")
    interview = relationship("Interview", backref="learning_notes", foreign_keys=[interview_id])

    __table_args__ = (
        Index("ix_learning_notes_user_type", "user_id", "note_type"),
        Index("ix_learning_notes_visibility", "visibility", "status"),
    )
