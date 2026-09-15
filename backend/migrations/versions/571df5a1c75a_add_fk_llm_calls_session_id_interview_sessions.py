"""add fk llm_calls.session_id -> interview_sessions.id

Revision ID: 571df5a1c75a
Revises: 88fa803fe9e3
Create Date: 2026-09-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "571df5a1c75a"
down_revision: str | Sequence[str] | None = "88fa803fe9e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE llm_calls SET session_id = NULL "
            "WHERE session_id IS NOT NULL "
            "AND session_id NOT IN (SELECT id FROM interview_sessions)"
        )
    )
    op.create_foreign_key(
        "fk_llm_calls_session_id_interview_sessions",
        "llm_calls",
        "interview_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_llm_calls_session_id_interview_sessions", "llm_calls", type_="foreignkey"
    )
