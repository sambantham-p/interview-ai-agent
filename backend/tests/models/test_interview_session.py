from app.constants.interview import INTERVIEW_PHASES
from app.models.interview_session import SESSION_STATUSES, InterviewSession


def test_table_name_and_columns() -> None:
    columns = InterviewSession.__table__.columns

    assert InterviewSession.__tablename__ == "interview_sessions"
    assert {c.name for c in columns} == {
        "id",
        "user_id",
        "candidate_profile_id",
        "job_description_id",
        "current_phase",
        "status",
        "transcript",
        "red_flag_count",
        "red_flag_warning_issued",
        "hint_counts",
        "end_reason",
        "question_pool",
        "asked_question_ids",
        "github_call_count",
        "company_research",
        "created_at",
        "ended_at",
    }


def test_user_id_has_no_default() -> None:
    assert InterviewSession.__table__.c.user_id.default is None


def test_current_phase_defaults_to_the_first_interview_phase() -> None:
    assert InterviewSession.__table__.c.current_phase.default.arg == INTERVIEW_PHASES[0]


def test_status_defaults_to_in_progress() -> None:
    assert InterviewSession.__table__.c.status.default.arg == SESSION_STATUSES[0]
    assert SESSION_STATUSES[0] == "in_progress"


def test_red_flag_count_defaults_to_zero() -> None:
    assert InterviewSession.__table__.c.red_flag_count.default.arg == 0


def test_red_flag_warning_issued_defaults_to_false() -> None:
    assert InterviewSession.__table__.c.red_flag_warning_issued.default.arg is False


def test_candidate_profile_id_and_job_description_id_are_cascading_foreign_keys() -> (
    None
):
    for col in (
        InterviewSession.__table__.c.candidate_profile_id,
        InterviewSession.__table__.c.job_description_id,
    ):
        assert {fk.ondelete for fk in col.foreign_keys} == {"CASCADE"}

    fk_targets = {
        fk.target_fullname
        for col in (
            InterviewSession.__table__.c.candidate_profile_id,
            InterviewSession.__table__.c.job_description_id,
        )
        for fk in col.foreign_keys
    }
    assert fk_targets == {"candidate_profiles.id", "job_descriptions.id"}


def test_user_id_is_a_cascading_foreign_key_to_users() -> None:
    fks = InterviewSession.__table__.c.user_id.foreign_keys
    assert {fk.target_fullname for fk in fks} == {"users.id"}
    assert {fk.ondelete for fk in fks} == {"CASCADE"}
