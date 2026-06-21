from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP
from .base import BaseModel


class Notification(BaseModel):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    notification_type = Column(String(30), nullable=False)
    related_id = Column(Integer, nullable=True)
    related_type = Column(String(30), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(TIMESTAMP(timezone=True), nullable=True)
