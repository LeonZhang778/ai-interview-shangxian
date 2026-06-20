from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from .base import BaseModel


class Feedback(BaseModel):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    feedback_type = Column(String(20), default="bug")  # bug / suggestion / other
    contact = Column(String(100), nullable=True)
    page_url = Column(String(500), nullable=True)
    screenshot_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")  # pending / processing / resolved / ignored
    admin_reply = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
