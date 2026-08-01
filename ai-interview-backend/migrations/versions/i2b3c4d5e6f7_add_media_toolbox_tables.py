"""add media toolbox tables

Revision ID: i2b3c4d5e6f7
Revises: h1a2b3c4d5e6
Create Date: 2026-08-01 13:20:00.000000

视频工具箱媒体文件、异步任务和生命周期事件。

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i2b3c4d5e6f7"
down_revision: Union[str, None] = "h1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("source_format", sa.String(length=20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("media_type IN ('video', 'audio', 'image')", name="ck_media_files_media_type"),
        sa.CheckConstraint("size_bytes > 0", name="ck_media_files_size_positive"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="ck_media_files_duration_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_media_files_id", "media_files", ["id"], unique=False)
    op.create_index("ix_media_files_user_id", "media_files", ["user_id"], unique=False)
    op.create_index("ix_media_files_storage_key", "media_files", ["storage_key"], unique=True)
    op.create_index("ix_media_files_expires_at", "media_files", ["expires_at"], unique=False)
    op.create_index("ix_media_files_user_expires", "media_files", ["user_id", "expires_at"], unique=False)

    op.create_table(
        "media_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("input_file_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("options_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("output_file_id", sa.Integer(), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_media_tasks_status",
        ),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_media_tasks_progress_range"),
        sa.CheckConstraint("retry_count >= 0", name="ck_media_tasks_retry_nonnegative"),
        sa.ForeignKeyConstraint(["output_file_id"], ["media_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_tasks_id", "media_tasks", ["id"], unique=False)
    op.create_index("ix_media_tasks_user_id", "media_tasks", ["user_id"], unique=False)
    op.create_index("ix_media_tasks_tool_name", "media_tasks", ["tool_name"], unique=False)
    op.create_index("ix_media_tasks_status", "media_tasks", ["status"], unique=False)
    op.create_index("ix_media_tasks_output_file_id", "media_tasks", ["output_file_id"], unique=False)
    op.create_index("ix_media_tasks_celery_task_id", "media_tasks", ["celery_task_id"], unique=False)
    op.create_index("ix_media_tasks_user_status_created", "media_tasks", ["user_id", "status", "created_at"], unique=False)

    op.create_table(
        "media_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=60), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["media_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_events_id", "media_events", ["id"], unique=False)
    op.create_index("ix_media_events_task_id", "media_events", ["task_id"], unique=False)
    op.create_index("ix_media_events_user_id", "media_events", ["user_id"], unique=False)
    op.create_index("ix_media_events_event_name", "media_events", ["event_name"], unique=False)
    op.create_index("ix_media_events_task_created", "media_events", ["task_id", "created_at"], unique=False)
    op.create_index("ix_media_events_user_created", "media_events", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_media_events_user_created", table_name="media_events")
    op.drop_index("ix_media_events_task_created", table_name="media_events")
    op.drop_index("ix_media_events_event_name", table_name="media_events")
    op.drop_index("ix_media_events_user_id", table_name="media_events")
    op.drop_index("ix_media_events_task_id", table_name="media_events")
    op.drop_index("ix_media_events_id", table_name="media_events")
    op.drop_table("media_events")

    op.drop_index("ix_media_tasks_user_status_created", table_name="media_tasks")
    op.drop_index("ix_media_tasks_celery_task_id", table_name="media_tasks")
    op.drop_index("ix_media_tasks_output_file_id", table_name="media_tasks")
    op.drop_index("ix_media_tasks_status", table_name="media_tasks")
    op.drop_index("ix_media_tasks_tool_name", table_name="media_tasks")
    op.drop_index("ix_media_tasks_user_id", table_name="media_tasks")
    op.drop_index("ix_media_tasks_id", table_name="media_tasks")
    op.drop_table("media_tasks")

    op.drop_index("ix_media_files_user_expires", table_name="media_files")
    op.drop_index("ix_media_files_expires_at", table_name="media_files")
    op.drop_index("ix_media_files_storage_key", table_name="media_files")
    op.drop_index("ix_media_files_user_id", table_name="media_files")
    op.drop_index("ix_media_files_id", table_name="media_files")
    op.drop_table("media_files")
