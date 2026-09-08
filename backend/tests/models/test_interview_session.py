from app.constants.app import DEFAULT_USER_ID
from app.models.interview_session import InterviewSession


def test_table_name_and_columns() -> None:
    columns = InterviewSession.__table__.columns

    assert InterviewSession.__tablename__ == "interview_sessions"
    assert {c.name for c in columns} == {
        "id",
        "user_id",
        "role_title",
        "seniority",
        "tech_stack",
        "coding_assessment_expected",
        "created_at",
    }


def test_user_id_defaults_to_the_single_hardcoded_user() -> None:
    assert InterviewSession.__table__.c.user_id.default.arg == DEFAULT_USER_ID


def test_coding_assessment_expected_defaults_to_false() -> None:
    assert InterviewSession.__table__.c.coding_assessment_expected.default.arg is False
