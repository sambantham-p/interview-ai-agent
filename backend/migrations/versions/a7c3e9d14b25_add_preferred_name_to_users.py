"""add preferred_name to users

Revision ID: a7c3e9d14b25
Revises: d5b8e1a3c7f2
Create Date: 2026-09-19 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9d14b25"
down_revision: str | Sequence[str] | None = "d5b8e1a3c7f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("preferred_name", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "preferred_name")
