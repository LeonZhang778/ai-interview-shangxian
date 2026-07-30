"""add notebooks table, notebook_id, search_vector

Revision ID: f2a3b3c4d5e6
Revises: e1a2b3c4d5e6
Create Date: 2026-07-30 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR


# revision identifiers, used by Alembic.
revision: str = 'f2a3b3c4d5e6'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== 1. 创建 notebooks 表 =====
    op.create_table(
        'notebooks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('notebooks.id', ondelete='CASCADE'), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('icon', sa.String(20), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notebooks_id', 'notebooks', ['id'])
    op.create_index('ix_notebooks_user_id', 'notebooks', ['user_id'])
    op.create_index('ix_notebooks_parent_id', 'notebooks', ['parent_id'])

    # ===== 2. learning_notes 添加 notebook_id =====
    op.add_column('learning_notes',
        sa.Column('notebook_id', sa.Integer(), sa.ForeignKey('notebooks.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('ix_learning_notes_notebook_id', 'learning_notes', ['notebook_id'])

    # ===== 3. 全文搜索：添加 search_vector 列 =====
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.add_column('learning_notes',
        sa.Column('search_vector', TSVECTOR(), nullable=True)
    )
    op.create_index('ix_learning_notes_search_vector',
        'learning_notes', ['search_vector'],
        postgresql_using='gin'
    )

    # 创建更新 search_vector 的触发器函数
    op.execute("""
    CREATE OR REPLACE FUNCTION learning_notes_search_update()
    RETURNS trigger AS $$
    BEGIN
        NEW.search_vector = to_tsvector('simple',
            COALESCE(NEW.title, '') || ' ' ||
            COALESCE(NEW.content, '') || ' ' ||
            COALESCE(NEW.tags, '')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 创建触发器，insert/update 时自动更新 search_vector
    op.execute("""
    CREATE TRIGGER trg_learning_notes_search
    BEFORE INSERT OR UPDATE OF title, content, tags
    ON learning_notes
    FOR EACH ROW
    EXECUTE FUNCTION learning_notes_search_update();
    """)

    # 为已有数据初始化 search_vector
    op.execute("""
    UPDATE learning_notes SET search_vector = to_tsvector('simple',
        COALESCE(title, '') || ' ' ||
        COALESCE(content, '') || ' ' ||
        COALESCE(tags, '')
    );
    """)


def downgrade() -> None:
    # 全文搜索
    op.execute("DROP TRIGGER IF EXISTS trg_learning_notes_search ON learning_notes")
    op.execute("DROP FUNCTION IF EXISTS learning_notes_search_update()")
    op.drop_index('ix_learning_notes_search_vector', table_name='learning_notes')
    op.drop_column('learning_notes', 'search_vector')

    # notebook_id
    op.drop_index('ix_learning_notes_notebook_id', table_name='learning_notes')
    op.drop_column('learning_notes', 'notebook_id')

    # notebooks 表
    op.drop_index('ix_notebooks_parent_id', table_name='notebooks')
    op.drop_index('ix_notebooks_user_id', table_name='notebooks')
    op.drop_index('ix_notebooks_id', table_name='notebooks')
    op.drop_table('notebooks')