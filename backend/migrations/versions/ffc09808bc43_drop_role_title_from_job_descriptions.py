"""drop role_title from job_descriptions

Revision ID: ffc09808bc43
Revises: e78f74112f48
Create Date: 2026-09-12 19:01:34.835547

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ffc09808bc43"
down_revision: str | Sequence[str] | None = "e78f74112f48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("job_descriptions", "role_title")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "job_descriptions",
        sa.Column(
            "role_title", sa.String(), nullable=False, server_default="unspecified"
        ),
    )
    op.alter_column("job_descriptions", "role_title", server_default=None)
