from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String

from .base import BaseModel


class WeaknessStat(BaseModel):
    __tablename__ = "weakness_stats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    keyword = Column(String(100), nullable=False)
    count = Column(Integer, nullable=False, default=0, server_default="0")
    avg_score = Column(Float, nullable=True)
    last_occurred_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_weakness_stats_user_keyword", "user_id", "keyword", unique=True),
    )
