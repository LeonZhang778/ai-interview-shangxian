from sqlalchemy import Column, Integer, String, Text, ForeignKey
from .base import BaseModel


class ImageTask(BaseModel):
    __tablename__ = "image_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    width = Column(Integer, default=512)
    height = Column(Integer, default=512)
    steps = Column(Integer, default=20)
    cfg_scale = Column(Integer, default=7)
    status = Column(String(20), default="pending", index=True)  # pending/processing/success/failed
    image_url = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
