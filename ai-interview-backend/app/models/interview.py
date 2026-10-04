from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel


class Interview(BaseModel):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    experience_id = Column(Integer, ForeignKey("experiences.id"), nullable=True)
    target_position = Column(String(255), nullable=True)
    difficulty = Column(String(20), default="medium")  # easy/medium/hard 面试难度
    total_questions = Column(Integer, default=5)
    status = Column(String(20), default="in_progress", server_default="in_progress")  # in_progress/completed 面试状态
    current_question_index = Column(Integer, nullable=False, default=0, server_default="0")
    questions_data = Column(JSONB, nullable=True)  # AI 生成的面试题目
    overall_score = Column(DECIMAL(3, 1), nullable=True)
    report = Column(Text, nullable=True)  # 最终评估报告 JSON
    share_token = Column(String(32), unique=True, nullable=True)
    is_shared = Column(Boolean, default=False)
    shared_at = Column(DateTime, nullable=True)

    # 关联关系
    user = relationship("User", backref="interviews")
    resume = relationship("Resume", back_populates="interviews")
    messages = relationship("InterviewMessage", back_populates="interview", order_by="InterviewMessage.id")
