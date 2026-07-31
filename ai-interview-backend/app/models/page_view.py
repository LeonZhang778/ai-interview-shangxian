from sqlalchemy import Column, Integer, String
from .base import BaseModel


class PageView(BaseModel):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    page_path = Column(String(512), nullable=False)
    ip = Column(String(64), nullable=True, index=True)
    country = Column(String(64), nullable=True, index=True)
    province = Column(String(128), nullable=True, index=True)
    user_agent = Column(String(512), nullable=True)
