"""add role to job_descriptions

Revision ID: e78f74112f48
Revises: 6e12052cc530
Create Date: 2026-09-12 18:57:50.791657

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e78f74112f48"
down_revision: str | Sequence[str] | None = "6e12052cc530"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "job_descriptions",
        sa.Column("role", sa.String(), nullable=False, server_default="unspecified"),
    )
    op.alter_column("job_descriptions", "role", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("job_descriptions", "role")
