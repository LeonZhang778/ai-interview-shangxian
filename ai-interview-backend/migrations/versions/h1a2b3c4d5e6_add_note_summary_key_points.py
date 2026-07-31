"""add_note_summary_key_points

Revision ID: h1a2b3c4d5e6
Revises: g0b1c2d3e4f5
Create Date: 2026-07-31 15:40:00.000000

学习笔记新增 AI 摘要(summary)与三级要点(key_points)字段。

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h1a2b3c4d5e6'
down_revision: Union[str, None] = 'g0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('learning_notes', sa.Column('summary', sa.String(length=300), nullable=True))
    op.add_column('learning_notes', sa.Column('key_points', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('learning_notes', 'key_points')
    op.drop_column('learning_notes', 'summary')
