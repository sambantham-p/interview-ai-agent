"""cascade-delete judge evaluations and reports with their interview session

Revision ID: d5b8e1a3c7f2
Revises: 9c4e2a7b5d10
Create Date: 2026-09-19 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b8e1a3c7f2"
down_revision: str | Sequence[str] | None = "9c4e2a7b5d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("judge_evaluations", "interview_reports")


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        constraint = f"{table}_session_id_fkey"
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint,
            table,
            "interview_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        constraint = f"{table}_session_id_fkey"
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, "interview_sessions", ["session_id"], ["id"]
        )
