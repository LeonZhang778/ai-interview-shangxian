"""add job description and gap analysis to interviews"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s1e2f3a4b5c6"
down_revision: Union[str, None] = "q9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("interviews")}
    if "job_description" not in columns:
        op.add_column("interviews", sa.Column("job_description", sa.Text(), nullable=True))
    if "gap_analysis" not in columns:
        op.add_column("interviews", sa.Column("gap_analysis", postgresql.JSONB(), nullable=True))
    if "gap_analysis_status" not in columns:
        op.add_column(
            "interviews",
            sa.Column(
                "gap_analysis_status",
                sa.String(length=20),
                nullable=False,
                server_default="not_requested",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("interviews")}
    for name in ("gap_analysis_status", "gap_analysis", "job_description"):
        if name in columns:
            op.drop_column("interviews", name)
