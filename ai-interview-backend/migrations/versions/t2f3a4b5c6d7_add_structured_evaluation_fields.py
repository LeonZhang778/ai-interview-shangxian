"""add versioned scoring rubric snapshots and structured evaluation details"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t2f3a4b5c6d7"
down_revision: Union[str, None] = "s1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    interview_columns = {column["name"] for column in inspector.get_columns("interviews")}
    if "scoring_rubric_version" not in interview_columns:
        op.add_column("interviews", sa.Column("scoring_rubric_version", sa.String(length=64), nullable=True))
    if "scoring_rubric" not in interview_columns:
        op.add_column("interviews", sa.Column("scoring_rubric", postgresql.JSONB(), nullable=True))

    message_columns = {column["name"] for column in inspector.get_columns("interview_messages")}
    if "score_details" not in message_columns:
        op.add_column("interview_messages", sa.Column("score_details", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    message_columns = {column["name"] for column in inspector.get_columns("interview_messages")}
    if "score_details" in message_columns:
        op.drop_column("interview_messages", "score_details")

    interview_columns = {column["name"] for column in inspector.get_columns("interviews")}
    if "scoring_rubric" in interview_columns:
        op.drop_column("interviews", "scoring_rubric")
    if "scoring_rubric_version" in interview_columns:
        op.drop_column("interviews", "scoring_rubric_version")
