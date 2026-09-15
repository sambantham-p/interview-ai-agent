"""create judge_evaluations and interview_reports tables

Revision ID: c632f1dd5399
Revises: a1c2e5f7b9d3
Create Date: 2026-09-15 05:04:55.706698

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c632f1dd5399"
down_revision: str | Sequence[str] | None = "a1c2e5f7b9d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interview_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("recommendation_tier", sa.String(), nullable=False),
        sa.Column(
            "weights_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "judge_evaluation_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interview_reports_session_id"),
        "interview_reports",
        ["session_id"],
        unique=False,
    )
    op.create_table(
        "judge_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("judge_name", sa.String(), nullable=False),
        sa.Column("dimension", sa.String(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_judge_evaluations_judge_name"),
        "judge_evaluations",
        ["judge_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_judge_evaluations_session_id"),
        "judge_evaluations",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_judge_evaluations_session_id"), table_name="judge_evaluations"
    )
    op.drop_index(
        op.f("ix_judge_evaluations_judge_name"), table_name="judge_evaluations"
    )
    op.drop_table("judge_evaluations")
    op.drop_index(
        op.f("ix_interview_reports_session_id"), table_name="interview_reports"
    )
    op.drop_table("interview_reports")
