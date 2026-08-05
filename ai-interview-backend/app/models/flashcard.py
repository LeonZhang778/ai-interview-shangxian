from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class Flashcard(BaseModel):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    note_id = Column(Integer, ForeignKey("learning_notes.id", ondelete="CASCADE"), nullable=True, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(String(20), nullable=False, default="auto")
    ease_factor = Column(Float, nullable=False, default=2.5)
    interval = Column(Integer, nullable=False, default=0)
    repetitions = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)
    last_quality = Column(Integer, nullable=True)

    user = relationship("User", backref="flashcards")
    note = relationship("LearningNote", backref="flashcards")

    __table_args__ = (
        Index("ix_flashcards_user_review", "user_id", "next_review_at"),
    )
