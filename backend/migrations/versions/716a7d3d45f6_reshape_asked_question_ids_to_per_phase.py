"""reshape asked_question_ids to per-phase dict

Revision ID: 716a7d3d45f6
Revises: f24bdb6d43a9
Create Date: 2026-09-14 02:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "716a7d3d45f6"
down_revision: str | Sequence[str] | None = "f24bdb6d43a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "UPDATE interview_sessions SET asked_question_ids = '{}'::jsonb "
        "WHERE jsonb_typeof(asked_question_ids) != 'object'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE interview_sessions SET asked_question_ids = '[]'::jsonb "
        "WHERE jsonb_typeof(asked_question_ids) != 'array'"
    )
