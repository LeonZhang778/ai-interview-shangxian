"""add media file soft delete timestamp

Revision ID: k4d5e6f7g8h9
Revises: j3c4d5e6f7g8
Create Date: 2026-08-04 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k4d5e6f7g8h9"
down_revision: Union[str, None] = "j3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_files",
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_media_files_deleted_at", "media_files", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_media_files_deleted_at", table_name="media_files")
    op.drop_column("media_files", "deleted_at")
