"""backfill user collections

补齐 user_collections 表。

为何单独一个迁移、且放在链尾：
  d8e9f0a1b2c3（add_collection_groups）会执行 op.add_column('user_collections', group_id)，
  即它假定 user_collections 已存在；因此本表必须排在它之前。
  又因为 group_id 及其外键由 d8e9f0a1b2c3 负责添加，本迁移只建「无 group_id」的版本，
  顺序执行后与模型定义一致。（历史上 d8e9f0a1b2c3 能在生产跑通，正是因为该表当时已由
  migrations/create_experiences_tables.sql 手工建好，且那份 SQL 同样不含 group_id。）

幂等：生产库该表是历史上手工 SQL 建的，已存在；直接 create_table 会让部署时的
alembic upgrade head 因 relation already exists 失败并中断部署，故先判断再建。

Revision ID: 2e19432c8498
Revises: f7a8b9c0d1e2
Create Date: 2026-10-04 17:29:05.343541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e19432c8498'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EXISTING_TABLES = None


def _existing_tables() -> set:
    global _EXISTING_TABLES
    if _EXISTING_TABLES is None:
        _EXISTING_TABLES = set(sa.inspect(op.get_bind()).get_table_names())
    return _EXISTING_TABLES


def upgrade() -> None:
    """Upgrade schema."""
    if 'user_collections' in _existing_tables():
        return

    op.create_table(
        'user_collections',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('experience_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['experience_id'], ['experiences.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'experience_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_collections')
