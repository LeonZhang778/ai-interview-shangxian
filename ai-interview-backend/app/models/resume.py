from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Resume(BaseModel):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    parsed_content = Column(Text, nullable=True)  # AI 解析后的 JSON 结构化数据
    analysis = Column(Text, nullable=True)  # AI 分析 JSON（优劣势/建议）
    target_position = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending/parsing/completed/failed
    # 关联关系
    user = relationship("User", backref="resumes")
    interviews = relationship("Interview", back_populates="resume")
'''
backref
正向：当前实例可访问关联 User
反向：User 实例可通过 .resumes 拿到所有简历
一【User】对多【Resume】

back_populates
resume.interviews  # 直接拿到这份简历的所有面试
interview.resume  # 直接拿到这场面试属于哪份简历

'''
