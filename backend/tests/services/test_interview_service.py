from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_mock import MockerFixture

from app.constants.github import (
    GITHUB_CALL_BUDGET_PER_SESSION,
    GITHUB_TOOL_LOOP_MAX_ROUNDS,
)
from app.constants.interview import DEFAULT_RED_FLAG_THRESHOLD, INTERVIEW_PHASES
from app.core.github_tools import GITHUB_TOOL_DISPATCH, GITHUB_TOOLS
from app.core.search_mcp_client import SearchTransientError
from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.schemas.interview import InterviewTurnOutput
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
    start_interview,
    submit_turn,
)


def _fake_candidate_profile() -> CandidateProfile:
    return CandidateProfile(
        id=1,
        education=[],
        experience=[],
        projects=[{"name": "Foo"}],
        skills=["Python"],
        github_url=None,
    )


def _fake_job_description(**overrides) -> JobDescription:
    defaults = {
        "id": 2,
        "role": "Backend Engineer",
        "company_name": None,
        "seniority": "senior",
        "tech_stack": ["Python"],
        "coding_assessment_expected": True,
    }
    defaults.update(overrides)
    return JobDescription(**defaults)


def _fake_session(**overrides) -> InterviewSession:
    defaults = {
        "id": 10,
        "candidate_profile_id": 1,
        "job_description_id": 2,
        "current_phase": INTERVIEW_PHASES[0],
        "status": "in_progress",
        "transcript": [{"role": "model", "text": "Hi, let's get started."}],
        "red_flag_count": 0,
        "red_flag_warning_issued": False,
        "hint_counts": {},
        "question_pool": [],
        "asked_question_ids": {},
        "github_call_count": 0,
    }
    defaults.update(overrides)
    return InterviewSession(**defaults)


def _mock_db(mocker: MockerFixture, *, get_side_effect) -> Any:
    fake_db = mocker.AsyncMock()
    fake_db.add = mocker.MagicMock()
    fake_db.get = mocker.AsyncMock(side_effect=get_side_effect)
    return fake_db


def _mock_generate_structured(mocker: MockerFixture, output: InterviewTurnOutput):
    return mocker.patch(
        "app.services.interview_service.generate_structured",
        new_callable=mocker.AsyncMock,
        return_value=output,
    )


async def test_start_interview_creates_session_and_opening_reply(
    mocker: MockerFixture,
) -> None:
    candidate_profile = _fake_candidate_profile()
    job_description = _fake_job_description()

    async def get_side_effect(model, _id):
        if model is CandidateProfile:
            return candidate_profile
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    fake_db = _mock_db(mocker, get_side_effect=get_side_effect)
    mocker.patch(
        "app.services.interview_service.prefetch_question_pool",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Welcome! Let's start with your background.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    session = await start_interview(
        candidate_profile_id=1, job_description_id=2, db=fake_db
    )

    assert session.current_phase == INTERVIEW_PHASES[0]
    assert (
        session.transcript[-1]["text"] == "Welcome! Let's start with your background."
    )
    assert session.question_pool == []
    fake_db.commit.assert_awaited_once()


async def test_start_interview_prefetches_company_research_when_company_name_set(
    mocker: MockerFixture,
) -> None:
    candidate_profile = _fake_candidate_profile()
    job_description = _fake_job_description(company_name="Acme Corp")

    async def get_side_effect(model, _id):
        if model is CandidateProfile:
            return candidate_profile
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    fake_db = _mock_db(mocker, get_side_effect=get_side_effect)
    mocker.patch(
        "app.services.interview_service.prefetch_question_pool",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )
    fake_search = mocker.patch(
        "app.services.interview_service.search_company_context",
        new_callable=mocker.AsyncMock,
        return_value="Acme makes widgets.",
    )
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Welcome!",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    session = await start_interview(
        candidate_profile_id=1, job_description_id=2, db=fake_db
    )

    assert session.company_research == "Acme makes widgets."
    fake_search.assert_awaited_once_with(
        company_name="Acme Corp", role="Backend Engineer"
    )


async def test_start_interview_skips_company_research_when_no_company_name(
    mocker: MockerFixture,
) -> None:
    candidate_profile = _fake_candidate_profile()
    job_description = _fake_job_description()

    async def get_side_effect(model, _id):
        if model is CandidateProfile:
            return candidate_profile
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    fake_db = _mock_db(mocker, get_side_effect=get_side_effect)
    mocker.patch(
        "app.services.interview_service.prefetch_question_pool",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )
    fake_search = mocker.patch(
        "app.services.interview_service.search_company_context",
        new_callable=mocker.AsyncMock,
    )
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Welcome!",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    session = await start_interview(
        candidate_profile_id=1, job_description_id=2, db=fake_db
    )

    assert session.company_research is None
    fake_search.assert_not_awaited()


async def test_start_interview_continues_when_company_research_fails(
    mocker: MockerFixture,
) -> None:
    candidate_profile = _fake_candidate_profile()
    job_description = _fake_job_description(company_name="Acme Corp")

    async def get_side_effect(model, _id):
        if model is CandidateProfile:
            return candidate_profile
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    fake_db = _mock_db(mocker, get_side_effect=get_side_effect)
    mocker.patch(
        "app.services.interview_service.prefetch_question_pool",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )
    mocker.patch(
        "app.services.interview_service.search_company_context",
        new_callable=mocker.AsyncMock,
        side_effect=SearchTransientError("mcp connection failed"),
    )
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Welcome!",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    session = await start_interview(
        candidate_profile_id=1, job_description_id=2, db=fake_db
    )

    assert session.company_research is None
    assert session.current_phase == INTERVIEW_PHASES[0]


async def test_start_interview_raises_when_candidate_profile_missing(
    mocker: MockerFixture,
) -> None:
    fake_db = _mock_db(mocker, get_side_effect=lambda model, _id: None)

    with pytest.raises(InterviewSessionNotFoundError, match="candidate profile"):
        await start_interview(candidate_profile_id=1, job_description_id=2, db=fake_db)


async def test_start_interview_raises_when_job_description_missing(
    mocker: MockerFixture,
) -> None:
    candidate_profile = _fake_candidate_profile()

    async def get_side_effect(model, _id):
        return candidate_profile if model is CandidateProfile else None

    fake_db = _mock_db(mocker, get_side_effect=get_side_effect)

    with pytest.raises(InterviewSessionNotFoundError, match="job description"):
        await start_interview(candidate_profile_id=1, job_description_id=2, db=fake_db)


async def test_submit_turn_raises_when_session_missing(mocker: MockerFixture) -> None:
    fake_db = _mock_db(mocker, get_side_effect=lambda model, _id: None)

    with pytest.raises(InterviewSessionNotFoundError):
        await submit_turn(session_id=99, message="hello", db=fake_db)


async def test_submit_turn_raises_when_session_not_in_progress(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(status="completed")
    fake_db = _mock_db(mocker, get_side_effect=lambda model, _id: session)

    with pytest.raises(InterviewSessionNotActiveError):
        await submit_turn(session_id=10, message="hello", db=fake_db)


async def _db_for_turn(
    mocker: MockerFixture,
    session: InterviewSession,
    *,
    job_description: JobDescription | None = None,
    candidate_profile: CandidateProfile | None = None,
):
    candidate_profile = candidate_profile or _fake_candidate_profile()
    job_description = job_description or _fake_job_description()

    async def get_side_effect(model, _id):
        if model is InterviewSession:
            return session
        if model is CandidateProfile:
            return candidate_profile
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    return _mock_db(mocker, get_side_effect=get_side_effect)


async def test_submit_turn_passes_unasked_pool_questions_and_marks_them_asked(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        current_phase="technical_interview",
        question_pool=[
            {"id": 1, "question_text": "What is ACID?", "topic": "DBMS"},
            {"id": 2, "question_text": "Explain the GIL.", "topic": "Python"},
        ],
        asked_question_ids={},
    )
    fake_db = await _db_for_turn(mocker, session)
    fake_generate = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Next question.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="answer", db=fake_db)

    system_instruction = fake_generate.call_args.kwargs["system_instruction"]
    assert "What is ACID?" in system_instruction
    assert "Explain the GIL." in system_instruction
    assert updated.asked_question_ids == {"technical_interview": [1, 2]}


async def test_submit_turn_never_reoffers_a_question_used_in_an_earlier_phase(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        current_phase="general_technical",
        question_pool=[
            {"id": 1, "question_text": "What is ACID?", "topic": "DBMS"},
            {"id": 2, "question_text": "Explain the GIL.", "topic": "Python"},
        ],
        asked_question_ids={"technical_interview": [1]},
    )
    fake_db = await _db_for_turn(mocker, session)
    fake_generate = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Next question.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="answer", db=fake_db)

    system_instruction = fake_generate.call_args.kwargs["system_instruction"]
    assert "What is ACID?" not in system_instruction
    assert "Explain the GIL." in system_instruction
    assert updated.asked_question_ids == {
        "technical_interview": [1],
        "general_technical": [2],
    }


async def test_submit_turn_injects_company_research_in_career_motivation_phase(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        current_phase="career_motivation",
        company_research="Acme Corp recently launched a new product line.",
    )
    fake_db = await _db_for_turn(mocker, session)
    fake_generate = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Why this role?",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    await submit_turn(session_id=10, message="answer", db=fake_db)

    system_instruction = fake_generate.call_args.kwargs["system_instruction"]
    assert "Acme Corp recently launched a new product line." in system_instruction


async def test_submit_turn_omits_company_research_outside_those_phases(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        current_phase="technical_interview",
        company_research="Acme Corp recently launched a new product line.",
    )
    fake_db = await _db_for_turn(mocker, session)
    fake_generate = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Next question.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    await submit_turn(session_id=10, message="answer", db=fake_db)

    system_instruction = fake_generate.call_args.kwargs["system_instruction"]
    assert "Acme Corp recently launched a new product line." not in system_instruction


async def test_submit_turn_reuses_the_same_batch_across_turns_in_one_phase(
    mocker: MockerFixture,
) -> None:
    # The bug this guards against: re-selecting a fresh batch every turn
    # (instead of once per phase) burns through the whole pool well
    # before the interview reaches its later phases - found via a live
    # end-to-end run, not a hypothetical.
    session = _fake_session(
        current_phase="technical_interview",
        question_pool=[
            {"id": 1, "question_text": "What is ACID?", "topic": "DBMS"},
            {"id": 2, "question_text": "Explain the GIL.", "topic": "Python"},
            {"id": 3, "question_text": "What is a closure?", "topic": "JavaScript"},
        ],
        asked_question_ids={},
    )
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="First question.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    first = await submit_turn(session_id=10, message="answer one", db=fake_db)
    assert first.asked_question_ids == {"technical_interview": [1, 2, 3]}

    second = await submit_turn(session_id=10, message="answer two", db=fake_db)
    assert second.asked_question_ids == {"technical_interview": [1, 2, 3]}


async def test_submit_turn_uses_github_tools_when_phase_is_project_drill_down_and_url_set(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase="project_drill_down")
    candidate_profile = _fake_candidate_profile()
    candidate_profile.github_url = "https://github.com/octocat"
    fake_db = await _db_for_turn(mocker, session, candidate_profile=candidate_profile)
    fake_generate_with_tools = mocker.patch(
        "app.services.interview_service.generate_structured_with_tools",
        new_callable=mocker.AsyncMock,
        return_value=InterviewTurnOutput(
            reply="Tell me about your project.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )
    fake_generate_plain = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="unused", phase_complete=False, red_flag=False, anxiety_detected=False
        ),
    )

    await submit_turn(session_id=10, message="It's a FastAPI app", db=fake_db)

    fake_generate_with_tools.assert_awaited_once()
    fake_generate_plain.assert_not_awaited()
    call_kwargs = fake_generate_with_tools.call_args.kwargs
    assert call_kwargs["max_rounds"] == GITHUB_TOOL_LOOP_MAX_ROUNDS
    assert call_kwargs["tools"] == GITHUB_TOOLS
    # tool_dispatch is wrapped for call counting (see
    # GITHUB_CALL_BUDGET_PER_SESSION) - same tool names, different
    # (wrapped) callables, so compare keys rather than dict equality.
    assert set(call_kwargs["tool_dispatch"].keys()) == set(GITHUB_TOOL_DISPATCH.keys())


async def test_submit_turn_skips_github_tools_once_budget_is_exhausted(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        current_phase="project_drill_down",
        github_call_count=GITHUB_CALL_BUDGET_PER_SESSION,
    )
    candidate_profile = _fake_candidate_profile()
    candidate_profile.github_url = "https://github.com/octocat"
    fake_db = await _db_for_turn(mocker, session, candidate_profile=candidate_profile)
    fake_generate_with_tools = mocker.patch(
        "app.services.interview_service.generate_structured_with_tools",
        new_callable=mocker.AsyncMock,
    )
    fake_generate_plain = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Let's continue.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    await submit_turn(session_id=10, message="tell me more", db=fake_db)

    fake_generate_plain.assert_awaited_once()
    fake_generate_with_tools.assert_not_awaited()


async def test_submit_turn_adds_actual_github_calls_made_to_the_session_counter(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase="project_drill_down", github_call_count=3)
    candidate_profile = _fake_candidate_profile()
    candidate_profile.github_url = "https://github.com/octocat"
    fake_db = await _db_for_turn(mocker, session, candidate_profile=candidate_profile)

    async def fake_generate_with_tools(**kwargs):
        # Simulate the tool loop making 2 real GitHub calls this turn.
        dispatch = kwargs["tool_dispatch"]
        await dispatch["list_repos"](username="octocat")
        await dispatch["list_repo_files"](owner="octocat", repo="hello-world")
        return InterviewTurnOutput(
            reply="Found it.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        )

    mocker.patch(
        "app.services.interview_service.generate_structured_with_tools",
        side_effect=fake_generate_with_tools,
    )
    mocker.patch("app.core.github_client.list_repos", new_callable=mocker.AsyncMock)
    mocker.patch(
        "app.core.github_client.list_repo_files", new_callable=mocker.AsyncMock
    )

    updated = await submit_turn(session_id=10, message="show me the repo", db=fake_db)

    assert updated.github_call_count == 5  # 3 already + 2 made this turn


async def test_submit_turn_skips_github_tools_when_no_github_url(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase="project_drill_down")
    fake_db = await _db_for_turn(mocker, session)  # default profile: github_url=None
    fake_generate_with_tools = mocker.patch(
        "app.services.interview_service.generate_structured_with_tools",
        new_callable=mocker.AsyncMock,
    )
    fake_generate_plain = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Tell me more.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    await submit_turn(session_id=10, message="It's a FastAPI app", db=fake_db)

    fake_generate_plain.assert_awaited_once()
    fake_generate_with_tools.assert_not_awaited()


async def test_submit_turn_skips_github_tools_outside_project_drill_down_phase(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase="technical_interview")
    candidate_profile = _fake_candidate_profile()
    candidate_profile.github_url = "https://github.com/octocat"
    fake_db = await _db_for_turn(mocker, session, candidate_profile=candidate_profile)
    fake_generate_with_tools = mocker.patch(
        "app.services.interview_service.generate_structured_with_tools",
        new_callable=mocker.AsyncMock,
    )
    fake_generate_plain = _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Next topic.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    await submit_turn(session_id=10, message="answer", db=fake_db)

    fake_generate_plain.assert_awaited_once()
    fake_generate_with_tools.assert_not_awaited()


async def test_submit_turn_advances_to_next_phase_when_complete(
    mocker: MockerFixture,
) -> None:
    session = _fake_session()
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Good, let's move on.",
            phase_complete=True,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="I worked at Acme", db=fake_db)

    assert updated.current_phase == INTERVIEW_PHASES[1]
    assert updated.status == "in_progress"
    assert updated.transcript[-1]["text"] == "Good, let's move on."


async def test_submit_turn_completes_interview_after_last_phase(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase=INTERVIEW_PHASES[-1])
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Thanks, that's everything.",
            phase_complete=True,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="No more questions", db=fake_db)

    assert updated.status == "completed"
    assert updated.ended_at is not None


async def test_submit_turn_increments_red_flag_count(mocker: MockerFixture) -> None:
    session = _fake_session()
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="That doesn't match your resume.",
            phase_complete=False,
            red_flag=True,
            red_flag_reason="Claimed a role not on the resume",
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="I was a CTO there", db=fake_db)

    assert updated.red_flag_count == 1
    assert updated.status == "in_progress"
    assert updated.red_flag_warning_issued is False


async def test_submit_turn_issues_warning_at_threshold(mocker: MockerFixture) -> None:
    session = _fake_session(red_flag_count=DEFAULT_RED_FLAG_THRESHOLD - 1)
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Hmm, that's inconsistent.",
            phase_complete=False,
            red_flag=True,
            red_flag_reason="Another inconsistency",
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="...", db=fake_db)

    assert updated.red_flag_count == DEFAULT_RED_FLAG_THRESHOLD
    assert updated.red_flag_warning_issued is True
    assert updated.status == "in_progress"
    assert "flag" in updated.transcript[-1]["text"].lower()


async def test_submit_turn_ends_early_after_warning_and_another_red_flag(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(
        red_flag_count=DEFAULT_RED_FLAG_THRESHOLD, red_flag_warning_issued=True
    )
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="That's a serious concern.",
            phase_complete=False,
            red_flag=True,
            red_flag_reason="One too many",
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(session_id=10, message="...", db=fake_db)

    assert updated.status == "ended_early"
    assert updated.end_reason == "red_flag_threshold"
    assert updated.ended_at is not None
    assert isinstance(updated.ended_at, datetime)
    assert updated.ended_at.tzinfo is UTC


async def test_submit_turn_ends_immediately_on_severe_red_flag_no_warning_needed(
    mocker: MockerFixture,
) -> None:
    # Abusive/vulgar language is a harder stop than the ordinary red-flag
    # escalation - one occurrence ends the interview even on a session
    # that never triggered a single ordinary red flag before.
    session = _fake_session(red_flag_count=0, red_flag_warning_issued=False)
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="I understand you're frustrated.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
            severe_red_flag=True,
            severe_red_flag_reason="Candidate used abusive language",
        ),
    )

    updated = await submit_turn(
        session_id=10,
        message="This interview is f***ing stupid, you idiot bot",
        db=fake_db,
    )

    assert updated.status == "ended_early"
    assert updated.end_reason == "abusive_language"
    assert updated.red_flag_warning_issued is True
    assert updated.red_flag_count == 1
    assert updated.ended_at is not None
    assert "not acceptable" in updated.transcript[-1]["text"]


async def test_submit_turn_severe_red_flag_does_not_advance_phase_even_if_marked_complete(
    mocker: MockerFixture,
) -> None:
    session = _fake_session()
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="That's not acceptable.",
            phase_complete=True,
            red_flag=False,
            anxiety_detected=False,
            severe_red_flag=True,
            severe_red_flag_reason="Abusive language",
        ),
    )

    updated = await submit_turn(session_id=10, message="go to hell", db=fake_db)

    assert updated.status == "ended_early"
    assert updated.current_phase == INTERVIEW_PHASES[0]


async def test_submit_turn_tracks_hint_count_per_phase(mocker: MockerFixture) -> None:
    session = _fake_session(current_phase=INTERVIEW_PHASES[2])
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Here's a nudge.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
            hint_level=1,
        ),
    )

    updated = await submit_turn(session_id=10, message="I'm not sure", db=fake_db)

    assert updated.hint_counts == {INTERVIEW_PHASES[2]: 1}


async def test_submit_turn_hint_count_is_independent_across_phases(
    mocker: MockerFixture,
) -> None:
    # A hint already logged for project_drill_down must not bleed into a
    # hint given later in technical_interview - each phase's count is its
    # own key, never a single interview-wide counter.
    session = _fake_session(
        current_phase=INTERVIEW_PHASES[2],
        hint_counts={INTERVIEW_PHASES[1]: 2},
    )
    fake_db = await _db_for_turn(mocker, session)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Here's a partial hint.",
            phase_complete=False,
            red_flag=False,
            anxiety_detected=False,
            hint_level=2,
        ),
    )

    updated = await submit_turn(session_id=10, message="still stuck", db=fake_db)

    assert updated.hint_counts == {INTERVIEW_PHASES[1]: 2, INTERVIEW_PHASES[2]: 1}


async def test_submit_turn_skips_coding_phase_when_jd_does_not_require_it(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase=INTERVIEW_PHASES[2])
    job_description = _fake_job_description()
    job_description.coding_assessment_expected = False
    fake_db = await _db_for_turn(mocker, session, job_description=job_description)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Good breadth of the stack covered.",
            phase_complete=True,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(
        session_id=10, message="That covers my experience", db=fake_db
    )

    assert INTERVIEW_PHASES[3] == "coding_challenge"
    assert updated.current_phase == INTERVIEW_PHASES[4]


async def test_submit_turn_enters_coding_phase_when_jd_requires_it(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(current_phase=INTERVIEW_PHASES[2])
    job_description = _fake_job_description()
    job_description.coding_assessment_expected = True
    fake_db = await _db_for_turn(mocker, session, job_description=job_description)
    _mock_generate_structured(
        mocker,
        InterviewTurnOutput(
            reply="Good breadth of the stack covered.",
            phase_complete=True,
            red_flag=False,
            anxiety_detected=False,
        ),
    )

    updated = await submit_turn(
        session_id=10, message="That covers my experience", db=fake_db
    )

    assert updated.current_phase == INTERVIEW_PHASES[3]
    assert updated.current_phase == "coding_challenge"
