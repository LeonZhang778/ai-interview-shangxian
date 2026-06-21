"""add interview share fields

Revision ID: f7a8b9c0d1e2
Revises: b5c6d7e8f9a0
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add share fields to interviews table
    op.add_column('interviews', sa.Column('share_token', sa.String(32), nullable=True))
    op.add_column('interviews', sa.Column('is_shared', sa.Boolean(), server_default='false'))
    op.add_column('interviews', sa.Column('shared_at', sa.TIMESTAMP(timezone=True), nullable=True))

    # Create unique index on share_token
    op.create_index('ix_interviews_share_token', 'interviews', ['share_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_interviews_share_token', table_name='interviews')
    op.drop_column('interviews', 'shared_at')
    op.drop_column('interviews', 'is_shared')
    op.drop_column('interviews', 'share_token')
