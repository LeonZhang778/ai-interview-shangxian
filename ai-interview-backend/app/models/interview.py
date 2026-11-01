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
    job_description = Column(Text, nullable=True)
    gap_analysis = Column(JSONB, nullable=True)
    gap_analysis_status = Column(
        String(20), nullable=False, default="not_requested", server_default="not_requested"
    )
    difficulty = Column(String(20), default="medium")  # easy/medium/hard 面试难度
    total_questions = Column(Integer, default=5)
    status = Column(String(20), default="in_progress", server_default="in_progress")  # in_progress/completed 面试状态
    # 报告就绪标记，与 status 分离（重要）：
    #   status=completed 只表示「问答结束」，report_status 才表示「报告能不能读」。
    #   报告生成已从请求路径搬到 Celery，最后一题提交后 status 立刻变 completed，
    #   而报告要几十秒后才就绪。若沿用「completed 即报告可读」的假设，
    #   用户点进报告页会看到空白。前端据此轮询，见 Report.vue / Interview.vue。
    # 取值：ready(可读) / pending(生成中) / failed(失败，可重试)
    # 默认 ready 是为了兼容两类历史数据：已生成过报告的旧面试，以及进行中的面试
    # （此时 report 为空，但 get_report 会先按 status 拦掉，不会暴露半成品）。
    report_status = Column(String(20), nullable=False, default="ready", server_default="ready")
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
