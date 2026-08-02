"""add media task error message

Revision ID: j3c4d5e6f7g8
Revises: i2b3c4d5e6f7
Create Date: 2026-08-02 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j3c4d5e6f7g8"
down_revision: Union[str, None] = "i2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_tasks", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_tasks", "error_message")
