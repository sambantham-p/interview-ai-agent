"""add content_hash to candidate_profiles and job_descriptions

Revision ID: 9c4e2a7b5d10
Revises: 3f7a1c9d2b64
Create Date: 2026-09-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c4e2a7b5d10"
down_revision: str | Sequence[str] | None = "3f7a1c9d2b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("candidate_profiles", "job_descriptions")


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.add_column(table, sa.Column("content_hash", sa.String(), nullable=True))
        op.create_unique_constraint(
            f"uq_{table}_user_content_hash", table, ["user_id", "content_hash"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES:
        op.drop_constraint(f"uq_{table}_user_content_hash", table, type_="unique")
        op.drop_column(table, "content_hash")
