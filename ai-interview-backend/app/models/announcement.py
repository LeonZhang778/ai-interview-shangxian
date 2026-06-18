from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from .base import BaseModel


class Announcement(BaseModel):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    announcement_type = Column(String(20), default="info")  # info/update/maintenance/activity
    level = Column(String(5), default="P1")  # P0=紧急 P1=重要 P2=普通
    is_pinned = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=False)
