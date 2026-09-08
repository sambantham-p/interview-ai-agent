from app.constants.app import DEFAULT_USER_ID
from app.models.candidate_profile import CandidateProfile


def test_table_name_and_columns() -> None:
    columns = CandidateProfile.__table__.columns

    assert CandidateProfile.__tablename__ == "candidate_profiles"
    assert {c.name for c in columns} == {
        "id",
        "user_id",
        "education",
        "experience",
        "projects",
        "skills",
        "github_url",
        "created_at",
    }


def test_user_id_defaults_to_the_single_hardcoded_user() -> None:
    assert CandidateProfile.__table__.c.user_id.default.arg == DEFAULT_USER_ID


def test_github_url_is_nullable() -> None:
    assert CandidateProfile.__table__.c.github_url.nullable is True
