"""add technical_questions (pgvector) and question pool tracking

Revision ID: f24bdb6d43a9
Revises: 571df5a1c75a
Create Date: 2026-09-14 01:00:00.000000

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f24bdb6d43a9"
down_revision: str | Sequence[str] | None = "571df5a1c75a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "technical_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_text", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column(
            "tech_stack",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("seniority", sa.String(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_technical_questions_topic", "technical_questions", ["topic"])
    op.create_index(
        "ix_technical_questions_difficulty", "technical_questions", ["difficulty"]
    )
    op.create_index(
        "ix_technical_questions_seniority", "technical_questions", ["seniority"]
    )

    op.add_column(
        "interview_sessions",
        sa.Column(
            "question_pool",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "interview_sessions",
        sa.Column(
            "asked_question_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.alter_column("interview_sessions", "question_pool", server_default=None)
    op.alter_column("interview_sessions", "asked_question_ids", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("interview_sessions", "asked_question_ids")
    op.drop_column("interview_sessions", "question_pool")
    op.drop_index("ix_technical_questions_seniority", table_name="technical_questions")
    op.drop_index("ix_technical_questions_difficulty", table_name="technical_questions")
    op.drop_index("ix_technical_questions_topic", table_name="technical_questions")
    op.drop_table("technical_questions")
