from app.models.judge_evaluation import JudgeEvaluation


def test_table_name_and_columns() -> None:
    columns = JudgeEvaluation.__table__.columns

    assert JudgeEvaluation.__tablename__ == "judge_evaluations"
    assert {c.name for c in columns} == {
        "id",
        "session_id",
        "judge_name",
        "dimension",
        "score",
        "summary",
        "evidence",
        "created_at",
    }


def test_evidence_defaults_to_an_empty_list() -> None:
    assert JudgeEvaluation.__table__.c.evidence.default.arg(None) == []


def test_session_id_and_judge_name_are_indexed() -> None:
    assert JudgeEvaluation.__table__.c.session_id.index is True
    assert JudgeEvaluation.__table__.c.judge_name.index is True


def test_session_id_is_a_foreign_key_to_interview_sessions() -> None:
    fk_targets = {
        fk.target_fullname for fk in JudgeEvaluation.__table__.c.session_id.foreign_keys
    }
    assert fk_targets == {"interview_sessions.id"}
