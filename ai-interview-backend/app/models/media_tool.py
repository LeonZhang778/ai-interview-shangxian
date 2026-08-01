from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Index, Integer, JSON, String, TIMESTAMP
from sqlalchemy.orm import relationship

from .base import BaseModel


class MediaFile(BaseModel):
    """媒体工具箱中的输入或输出文件元数据。"""

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False, unique=True, index=True)
    original_name = Column(String(255), nullable=False)
    media_type = Column(String(20), nullable=False)
    source_format = Column(String(20), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    duration_ms = Column(BigInteger, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)

    user = relationship("User", backref="media_files")
    output_tasks = relationship(
        "MediaTask",
        back_populates="output_file",
        foreign_keys="MediaTask.output_file_id",
    )

    __table_args__ = (
        CheckConstraint("media_type IN ('video', 'audio', 'image')", name="ck_media_files_media_type"),
        CheckConstraint("size_bytes > 0", name="ck_media_files_size_positive"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_media_files_duration_nonnegative"),
        Index("ix_media_files_user_expires", "user_id", "expires_at"),
    )


class MediaTask(BaseModel):
    """异步媒体处理任务。"""

    __tablename__ = "media_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(40), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    input_file_ids = Column(JSON, nullable=False)
    options_json = Column(JSON, nullable=False, default=dict)
    output_file_id = Column(Integer, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True, index=True)
    progress = Column(Integer, nullable=False, default=0)
    error_code = Column(String(80), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    celery_task_id = Column(String(255), nullable=True, index=True)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    finished_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", backref="media_tasks")
    output_file = relationship("MediaFile", back_populates="output_tasks", foreign_keys=[output_file_id])
    events = relationship("MediaEvent", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_media_tasks_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_media_tasks_progress_range"),
        CheckConstraint("retry_count >= 0", name="ck_media_tasks_retry_nonnegative"),
        Index("ix_media_tasks_user_status_created", "user_id", "status", "created_at"),
    )


class MediaEvent(BaseModel):
    """媒体任务生命周期事件。"""

    __tablename__ = "media_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("media_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_name = Column(String(60), nullable=False, index=True)
    payload_json = Column(JSON, nullable=True)

    task = relationship("MediaTask", back_populates="events")
    user = relationship("User", backref="media_events")

    __table_args__ = (
        Index("ix_media_events_task_created", "task_id", "created_at"),
        Index("ix_media_events_user_created", "user_id", "created_at"),
    )
