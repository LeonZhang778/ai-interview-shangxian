"""add_page_view_geo_fields

Revision ID: g0b1c2d3e4f5
Revises: f2a3b3c4d5e6
Create Date: 2026-07-31 11:30:00.000000

新增 page_views 的 IP / 国家 / 省份 / User-Agent 字段，用于活跃度追踪的地理分布分析。

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g0b1c2d3e4f5'
down_revision: Union[str, None] = 'f2a3b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('page_views', sa.Column('ip', sa.String(length=64), nullable=True))
    op.add_column('page_views', sa.Column('country', sa.String(length=64), nullable=True))
    op.add_column('page_views', sa.Column('province', sa.String(length=128), nullable=True))
    op.add_column('page_views', sa.Column('user_agent', sa.String(length=512), nullable=True))
    op.create_index('ix_page_views_ip', 'page_views', ['ip'])
    op.create_index('ix_page_views_country', 'page_views', ['country'])
    op.create_index('ix_page_views_province', 'page_views', ['province'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_page_views_province', table_name='page_views')
    op.drop_index('ix_page_views_country', table_name='page_views')
    op.drop_index('ix_page_views_ip', table_name='page_views')
    op.drop_column('page_views', 'user_agent')
    op.drop_column('page_views', 'province')
    op.drop_column('page_views', 'country')
    op.drop_column('page_views', 'ip')
