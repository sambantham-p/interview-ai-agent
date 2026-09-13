"""rename interview_sessions to job_descriptions

Revision ID: 6e12052cc530
Revises: 2563a7bc0a86
Create Date: 2026-09-09 21:11:34.250204

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6e12052cc530"
down_revision: str | Sequence[str] | None = "2563a7bc0a86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("interview_sessions", "job_descriptions")
    op.execute(
        "ALTER INDEX ix_interview_sessions_user_id RENAME TO ix_job_descriptions_user_id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER INDEX ix_job_descriptions_user_id RENAME TO ix_interview_sessions_user_id"
    )
    op.rename_table("job_descriptions", "interview_sessions")
