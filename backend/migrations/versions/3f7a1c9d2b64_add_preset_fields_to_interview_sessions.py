"""add preset/time-budget fields to interview_sessions

Revision ID: 3f7a1c9d2b64
Revises: 1b82acda8d08
Create Date: 2026-09-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3f7a1c9d2b64"
down_revision: str | Sequence[str] | None = "1b82acda8d08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    for column in ("selected_phases", "phase_time_budget"):
        default = "'[]'::jsonb" if column == "selected_phases" else "'{}'::jsonb"
        op.add_column(
            "interview_sessions",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text(default),
            ),
        )
        op.alter_column("interview_sessions", column, server_default=None)
    op.add_column(
        "interview_sessions", sa.Column("duration_minutes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "interview_sessions",
        sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "phase_started_at")
    op.drop_column("interview_sessions", "duration_minutes")
    op.drop_column("interview_sessions", "phase_time_budget")
    op.drop_column("interview_sessions", "selected_phases")
