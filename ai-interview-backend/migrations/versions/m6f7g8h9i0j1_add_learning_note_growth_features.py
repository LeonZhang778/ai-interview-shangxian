"""add learning note growth features

Revision ID: m6f7g8h9i0j1
Revises: l5e6f7g8h9i0
Create Date: 2026-08-05 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m6f7g8h9i0j1"
down_revision: Union[str, None] = "l5e6f7g8h9i0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "learning_notes",
        sa.Column("collect_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "learning_notes",
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "learning_notes",
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "public_note_likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["learning_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "user_id", name="uq_public_note_like_user"),
    )
    op.create_index("ix_public_note_likes_id", "public_note_likes", ["id"])
    op.create_index("ix_public_note_likes_note_id", "public_note_likes", ["note_id"])
    op.create_index("ix_public_note_likes_user_id", "public_note_likes", ["user_id"])

    op.create_table(
        "public_note_collections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["learning_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "user_id", name="uq_public_note_collection_user"),
    )
    op.create_index("ix_public_note_collections_id", "public_note_collections", ["id"])
    op.create_index("ix_public_note_collections_note_id", "public_note_collections", ["note_id"])
    op.create_index("ix_public_note_collections_user_id", "public_note_collections", ["user_id"])

    op.create_table(
        "public_note_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["learning_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["public_note_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_note_comments_id", "public_note_comments", ["id"])
    op.create_index("ix_public_note_comments_note_id", "public_note_comments", ["note_id"])
    op.create_index("ix_public_note_comments_user_id", "public_note_comments", ["user_id"])
    op.create_index("ix_public_note_comments_parent_id", "public_note_comments", ["parent_id"])
    op.create_index(
        "ix_public_note_comments_note_parent_created",
        "public_note_comments",
        ["note_id", "parent_id", "created_at"],
    )

    op.create_table(
        "flashcards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="auto"),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_review_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("last_quality", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["learning_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flashcards_id", "flashcards", ["id"])
    op.create_index("ix_flashcards_user_id", "flashcards", ["user_id"])
    op.create_index("ix_flashcards_note_id", "flashcards", ["note_id"])
    op.create_index("ix_flashcards_user_review", "flashcards", ["user_id", "next_review_at"])

    op.create_table(
        "weakness_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Float(), nullable=True),
        sa.Column("last_occurred_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weakness_stats_id", "weakness_stats", ["id"])
    op.create_index("ix_weakness_stats_user_id", "weakness_stats", ["user_id"])
    op.create_index("ix_weakness_stats_user_keyword", "weakness_stats", ["user_id", "keyword"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_weakness_stats_user_keyword", table_name="weakness_stats")
    op.drop_index("ix_weakness_stats_user_id", table_name="weakness_stats")
    op.drop_index("ix_weakness_stats_id", table_name="weakness_stats")
    op.drop_table("weakness_stats")

    op.drop_index("ix_flashcards_user_review", table_name="flashcards")
    op.drop_index("ix_flashcards_note_id", table_name="flashcards")
    op.drop_index("ix_flashcards_user_id", table_name="flashcards")
    op.drop_index("ix_flashcards_id", table_name="flashcards")
    op.drop_table("flashcards")

    op.drop_index("ix_public_note_comments_note_parent_created", table_name="public_note_comments")
    op.drop_index("ix_public_note_comments_parent_id", table_name="public_note_comments")
    op.drop_index("ix_public_note_comments_user_id", table_name="public_note_comments")
    op.drop_index("ix_public_note_comments_note_id", table_name="public_note_comments")
    op.drop_index("ix_public_note_comments_id", table_name="public_note_comments")
    op.drop_table("public_note_comments")

    op.drop_index("ix_public_note_collections_user_id", table_name="public_note_collections")
    op.drop_index("ix_public_note_collections_note_id", table_name="public_note_collections")
    op.drop_index("ix_public_note_collections_id", table_name="public_note_collections")
    op.drop_table("public_note_collections")

    op.drop_index("ix_public_note_likes_user_id", table_name="public_note_likes")
    op.drop_index("ix_public_note_likes_note_id", table_name="public_note_likes")
    op.drop_index("ix_public_note_likes_id", table_name="public_note_likes")
    op.drop_table("public_note_likes")

    op.drop_column("learning_notes", "published_at")
    op.drop_column("learning_notes", "comment_count")
    op.drop_column("learning_notes", "collect_count")
