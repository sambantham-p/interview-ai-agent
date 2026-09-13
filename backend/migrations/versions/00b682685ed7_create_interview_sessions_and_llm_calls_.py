"""create interview_sessions and llm_calls tables

Revision ID: 00b682685ed7
Revises: ffc09808bc43
Create Date: 2026-09-13 12:05:52.047001

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00b682685ed7"
down_revision: str | Sequence[str] | None = "ffc09808bc43"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("response", sa.String(), nullable=False),
        sa.Column("prompt_token_count", sa.Integer(), nullable=True),
        sa.Column("candidates_token_count", sa.Integer(), nullable=True),
        sa.Column("total_token_count", sa.Integer(), nullable=True),
        sa.Column("latency_seconds", sa.Float(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_calls_session_id"), "llm_calls", ["session_id"], unique=False
    )
    op.create_index(op.f("ix_llm_calls_task"), "llm_calls", ["task"], unique=False)
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("job_description_id", sa.Integer(), nullable=False),
        sa.Column("current_phase", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "transcript", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("red_flag_count", sa.Integer(), nullable=False),
        sa.Column("red_flag_warning_issued", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
        sa.ForeignKeyConstraint(["job_description_id"], ["job_descriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interview_sessions_candidate_profile_id"),
        "interview_sessions",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_sessions_job_description_id"),
        "interview_sessions",
        ["job_description_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interview_sessions_user_id"),
        "interview_sessions",
        ["user_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_interview_sessions_user_id"), table_name="interview_sessions"
    )
    op.drop_index(
        op.f("ix_interview_sessions_job_description_id"),
        table_name="interview_sessions",
    )
    op.drop_index(
        op.f("ix_interview_sessions_candidate_profile_id"),
        table_name="interview_sessions",
    )
    op.drop_table("interview_sessions")
    op.drop_index(op.f("ix_llm_calls_task"), table_name="llm_calls")
    op.drop_index(op.f("ix_llm_calls_session_id"), table_name="llm_calls")
    op.drop_table("llm_calls")
    # ### end Alembic commands ###
