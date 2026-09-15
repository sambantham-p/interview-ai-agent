"""add end_reason to interview_sessions

Revision ID: ed18f2bb1c91
Revises: 00b682685ed7
Create Date: 2026-09-13 12:54:35.680258

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed18f2bb1c91"
down_revision: str | Sequence[str] | None = "00b682685ed7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "interview_sessions", sa.Column("end_reason", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "end_reason")
