"""add company_name to job_descriptions and company_research to interview_sessions

Revision ID: a1c2e5f7b9d3
Revises: 1120844cc303
Create Date: 2026-09-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c2e5f7b9d3"
down_revision: str | Sequence[str] | None = "1120844cc303"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_descriptions", sa.Column("company_name", sa.String(), nullable=True)
    )
    op.add_column(
        "interview_sessions",
        sa.Column("company_research", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "company_research")
    op.drop_column("job_descriptions", "company_name")
