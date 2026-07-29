"""add learning_notes table

Revision ID: e1a2b3c4d5e6
Revises: d8e9f0a1b2c3
Create Date: 2026-07-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'learning_notes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('note_type', sa.String(20), nullable=False, server_default='note'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='private'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('view_count', sa.Integer(), server_default='0'),
        sa.Column('like_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_learning_notes_id', 'learning_notes', ['id'])
    op.create_index('ix_learning_notes_user_id', 'learning_notes', ['user_id'])
    op.create_index('ix_learning_notes_interview_id', 'learning_notes', ['interview_id'])
    op.create_index('ix_learning_notes_user_type', 'learning_notes', ['user_id', 'note_type'])
    op.create_index('ix_learning_notes_visibility', 'learning_notes', ['visibility', 'status'])


def downgrade() -> None:
    op.drop_index('ix_learning_notes_visibility', table_name='learning_notes')
    op.drop_index('ix_learning_notes_user_type', table_name='learning_notes')
    op.drop_index('ix_learning_notes_interview_id', table_name='learning_notes')
    op.drop_index('ix_learning_notes_user_id', table_name='learning_notes')
    op.drop_index('ix_learning_notes_id', table_name='learning_notes')
    op.drop_table('learning_notes')
