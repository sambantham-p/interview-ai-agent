from app.models.llm_call import LLMCall


def test_table_name_and_columns() -> None:
    columns = LLMCall.__table__.columns

    assert LLMCall.__tablename__ == "llm_calls"
    assert {c.name for c in columns} == {
        "id",
        "task",
        "model",
        "session_id",
        "prompt",
        "response",
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "latency_seconds",
        "error",
        "extra",
        "created_at",
    }


def test_extra_defaults_to_an_empty_dict() -> None:
    assert LLMCall.__table__.c.extra.default.arg(None) == {}


def test_session_id_and_error_are_nullable() -> None:
    assert LLMCall.__table__.c.session_id.nullable is True
    assert LLMCall.__table__.c.error.nullable is True
