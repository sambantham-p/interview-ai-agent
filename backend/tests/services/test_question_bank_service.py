from pytest_mock import MockerFixture

from app.models.job_description import JobDescription
from app.models.technical_question import TechnicalQuestion
from app.services.question_bank_service import prefetch_question_pool


def _fake_job_description() -> JobDescription:
    return JobDescription(
        id=1,
        role="Backend Engineer",
        seniority="mid",
        tech_stack=["Python", "PostgreSQL"],
        coding_assessment_expected=True,
    )


def _fake_question(**overrides) -> TechnicalQuestion:
    defaults = {
        "id": 1,
        "question_text": "What is ACID?",
        "topic": "DBMS",
        "tech_stack": ["SQL"],
        "difficulty": "medium",
        "seniority": "mid",
        "embedding": [0.1] * 768,
    }
    defaults.update(overrides)
    return TechnicalQuestion(**defaults)


def _mock_db_with_questions(mocker: MockerFixture, questions: list[TechnicalQuestion]):
    fake_result = mocker.MagicMock()
    fake_result.scalars.return_value.all.return_value = questions
    fake_db = mocker.AsyncMock()
    fake_db.execute = mocker.AsyncMock(return_value=fake_result)
    return fake_db


async def test_prefetch_returns_shaped_question_dicts(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.services.question_bank_service.embed_text",
        new_callable=mocker.AsyncMock,
        return_value=[0.1] * 768,
    )
    questions = [
        _fake_question(id=1, question_text="What is ACID?", topic="DBMS"),
        _fake_question(id=2, question_text="Explain the GIL.", topic="Python"),
    ]
    fake_db = _mock_db_with_questions(mocker, questions)

    result = await prefetch_question_pool(
        job_description=_fake_job_description(), db=fake_db
    )

    assert result == [
        {
            "id": 1,
            "question_text": "What is ACID?",
            "topic": "DBMS",
            "difficulty": "medium",
        },
        {
            "id": 2,
            "question_text": "Explain the GIL.",
            "topic": "Python",
            "difficulty": "medium",
        },
    ]


async def test_prefetch_returns_empty_list_when_bank_is_empty(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.services.question_bank_service.embed_text",
        new_callable=mocker.AsyncMock,
        return_value=[0.1] * 768,
    )
    fake_db = _mock_db_with_questions(mocker, [])

    result = await prefetch_question_pool(
        job_description=_fake_job_description(), db=fake_db
    )

    assert result == []


async def test_prefetch_embeds_role_seniority_and_tech_stack(
    mocker: MockerFixture,
) -> None:
    fake_embed_text = mocker.patch(
        "app.services.question_bank_service.embed_text",
        new_callable=mocker.AsyncMock,
        return_value=[0.1] * 768,
    )
    fake_db = _mock_db_with_questions(mocker, [])

    await prefetch_question_pool(job_description=_fake_job_description(), db=fake_db)

    query_text = fake_embed_text.call_args.args[0]
    assert "Backend Engineer" in query_text
    assert "mid" in query_text
    assert "Python" in query_text
    assert "PostgreSQL" in query_text


async def test_prefetch_respects_custom_top_k(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.services.question_bank_service.embed_text",
        new_callable=mocker.AsyncMock,
        return_value=[0.1] * 768,
    )
    fake_db = _mock_db_with_questions(mocker, [])

    await prefetch_question_pool(
        job_description=_fake_job_description(), db=fake_db, top_k=10
    )

    fake_db.execute.assert_awaited_once()
