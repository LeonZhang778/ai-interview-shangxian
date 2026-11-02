from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel


class InterviewMessage(BaseModel):
    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # interviewer(面试官)/candidate(候选人)
    content = Column(Text, nullable=False)
    question_index = Column(Integer, nullable=True)
    score = Column(DECIMAL(3, 1), nullable=True)
    feedback = Column(Text, nullable=True)
    score_details = Column(JSONB, nullable=True)

    # 每场面试的每一题同一角色只允许一条记录。
    # 幂等此前只靠应用层「先查后写」，并发下两个请求可能同时查不到，于是同题被写两次、
    # current_question_index 被推进两次 —— 用户会莫名少答一题。这里把它变成数据库不变量。
    # question_index 可空（历史数据），Postgres 视 NULL 互不相等，不会误伤。
    __table_args__ = (
        UniqueConstraint(
            "interview_id", "role", "question_index",
            name="uq_interview_message_question",
        ),
    )

    # 关联关系
    interview = relationship("Interview", back_populates="messages")
