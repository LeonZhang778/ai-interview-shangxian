"""add notifications table and interview practice fields

Revision ID: b5c6d7e8f9a0
Revises: a3b2c1d4e5f6
Create Date: 2026-06-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, None] = '5041c767fd0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('notification_type', sa.String(30), nullable=False),
        sa.Column('related_id', sa.Integer(), nullable=True),
        sa.Column('related_type', sa.String(30), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_id', 'notifications', ['id'])

    # Make interview.resume_id nullable
    op.alter_column('interviews', 'resume_id', nullable=True)

    # Add experience_id to interviews
    op.add_column('interviews', sa.Column('experience_id', sa.Integer(), sa.ForeignKey('experiences.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('interviews', 'experience_id')
    op.alter_column('interviews', 'resume_id', nullable=False)
    op.drop_index('ix_notifications_id', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
