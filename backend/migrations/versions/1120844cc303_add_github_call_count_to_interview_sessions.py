"""add github_call_count to interview_sessions

Revision ID: 1120844cc303
Revises: 716a7d3d45f6
Create Date: 2026-09-14 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1120844cc303"
down_revision: str | Sequence[str] | None = "716a7d3d45f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "interview_sessions",
        sa.Column(
            "github_call_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column("interview_sessions", "github_call_count", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "github_call_count")
