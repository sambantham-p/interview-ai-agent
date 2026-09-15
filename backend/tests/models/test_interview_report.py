from app.models.interview_report import InterviewReport


def test_table_name_and_columns() -> None:
    columns = InterviewReport.__table__.columns

    assert InterviewReport.__tablename__ == "interview_reports"
    assert {c.name for c in columns} == {
        "id",
        "session_id",
        "overall_score",
        "recommendation_tier",
        "weights_used",
        "judge_evaluation_ids",
        "created_at",
    }


def test_weights_used_and_judge_evaluation_ids_default_empty() -> None:
    assert InterviewReport.__table__.c.weights_used.default.arg(None) == {}
    assert InterviewReport.__table__.c.judge_evaluation_ids.default.arg(None) == []


def test_session_id_is_a_foreign_key_to_interview_sessions() -> None:
    fk_targets = {
        fk.target_fullname for fk in InterviewReport.__table__.c.session_id.foreign_keys
    }
    assert fk_targets == {"interview_sessions.id"}
