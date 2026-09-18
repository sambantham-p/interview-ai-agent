"""add user_id FKs to users.id and ondelete cascade policies

Revision ID: 1b82acda8d08
Revises: fb118a0e1fc1
Create Date: 2026-09-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b82acda8d08"
down_revision: str | Sequence[str] | None = "fb118a0e1fc1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_fk_name(bind: sa.engine.Connection, table: str, column: str) -> str:
    """Look up an auto-named FK's real constraint name instead of guessing it."""
    result = bind.execute(
        sa.text(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = :table
              AND kcu.column_name = :column
            """
        ),
        {"table": table, "column": column},
    ).scalar()
    if result is None:
        raise RuntimeError(f"no existing foreign key found on {table}.{column}")
    return result


_ORPHAN_CHECK_TABLES = ("candidate_profiles", "job_descriptions", "interview_sessions")


def _assert_no_orphans(bind: sa.engine.Connection, table: str) -> None:
    """Fail loudly instead of adding a FK that would reject existing rows."""
    if table not in _ORPHAN_CHECK_TABLES:
        # Table/column identifiers can't be bound as SQL parameters (only
        # values can) - this allowlist is what actually makes the f-string
        # below safe, not just today's hardcoded call sites in upgrade().
        raise ValueError(f"{table!r} is not one of {_ORPHAN_CHECK_TABLES}")

    orphan_count = bind.execute(
        sa.text(
            f"""
            SELECT count(*) FROM {table} t
            LEFT JOIN users u ON u.id = t.user_id
            WHERE u.id IS NULL
            """  # nosec B608 - table is validated against a fixed allowlist above
        )
    ).scalar()
    if orphan_count:
        raise RuntimeError(
            f"{table} has {orphan_count} row(s) with a user_id not present in "
            "users - resolve these manually before adding the foreign key"
        )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    for table in ("candidate_profiles", "job_descriptions", "interview_sessions"):
        _assert_no_orphans(bind, table)

    candidate_profile_fk = _existing_fk_name(
        bind, "interview_sessions", "candidate_profile_id"
    )
    job_description_fk = _existing_fk_name(
        bind, "interview_sessions", "job_description_id"
    )

    op.drop_constraint(candidate_profile_fk, "interview_sessions", type_="foreignkey")
    op.create_foreign_key(
        "fk_interview_sessions_candidate_profile_id_candidate_profiles",
        "interview_sessions",
        "candidate_profiles",
        ["candidate_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(job_description_fk, "interview_sessions", type_="foreignkey")
    op.create_foreign_key(
        "fk_interview_sessions_job_description_id_job_descriptions",
        "interview_sessions",
        "job_descriptions",
        ["job_description_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_candidate_profiles_user_id_users",
        "candidate_profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_job_descriptions_user_id_users",
        "job_descriptions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_interview_sessions_user_id_users",
        "interview_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_interview_sessions_user_id_users",
        "interview_sessions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_job_descriptions_user_id_users", "job_descriptions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_candidate_profiles_user_id_users",
        "candidate_profiles",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_interview_sessions_job_description_id_job_descriptions",
        "interview_sessions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "interview_sessions",
        "job_descriptions",
        ["job_description_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_interview_sessions_candidate_profile_id_candidate_profiles",
        "interview_sessions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "interview_sessions",
        "candidate_profiles",
        ["candidate_profile_id"],
        ["id"],
    )
