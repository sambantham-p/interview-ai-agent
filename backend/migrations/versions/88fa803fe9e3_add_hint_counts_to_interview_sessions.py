"""add hint_counts to interview_sessions

Revision ID: 88fa803fe9e3
Revises: ed18f2bb1c91
Create Date: 2026-09-13 13:43:27.937583

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "88fa803fe9e3"
down_revision: str | Sequence[str] | None = "ed18f2bb1c91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "interview_sessions",
        sa.Column(
            "hint_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("interview_sessions", "hint_counts", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "hint_counts")
