"""add_page_views_table

Revision ID: a3b2c1d4e5f6
Revises: 11a22b3aa964
Create Date: 2026-06-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b2c1d4e5f6'
down_revision: Union[str, None] = '11a22b3aa964'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('page_views',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('session_id', sa.String(length=64), nullable=True),
    sa.Column('page_path', sa.String(length=512), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_page_views_user_id', 'page_views', ['user_id'])
    op.create_index('ix_page_views_session_id', 'page_views', ['session_id'])
    op.create_index('ix_page_views_created_at', 'page_views', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_page_views_created_at', table_name='page_views')
    op.drop_index('ix_page_views_session_id', table_name='page_views')
    op.drop_index('ix_page_views_user_id', table_name='page_views')
    op.drop_table('page_views')
