"""add collection groups for favorites grouping

Revision ID: d8e9f0a1b2c3
Revises: b5c6d7e8f9a0
Create Date: 2026-06-21 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = '2e19432c8498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create collection_groups table
    op.create_table(
        'collection_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_collection_groups_id', 'collection_groups', ['id'])
    op.create_index('ix_collection_groups_user_id', 'collection_groups', ['user_id'])

    # Add group_id column to user_collections
    op.add_column('user_collections', sa.Column('group_id', sa.Integer(), nullable=True))
    op.create_index('ix_user_collections_group_id', 'user_collections', ['group_id'])
    op.create_foreign_key(
        'fk_user_collections_group_id',
        'user_collections',
        'collection_groups',
        ['group_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_user_collections_group_id', 'user_collections', type_='foreignkey')
    op.drop_index('ix_user_collections_group_id', table_name='user_collections')
    op.drop_column('user_collections', 'group_id')
    op.drop_index('ix_collection_groups_user_id', table_name='collection_groups')
    op.drop_index('ix_collection_groups_id', table_name='collection_groups')
    op.drop_table('collection_groups')
