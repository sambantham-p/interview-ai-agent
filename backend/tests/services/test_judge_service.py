from typing import Any

import pytest
from pytest_mock import MockerFixture

from app.constants.judge import (
    ATTITUDE_ABUSIVE_LANGUAGE_SCORE_CAP,
    JUDGE_ATTITUDE,
    JUDGE_CAREER_FIT,
    JUDGE_CODING,
    JUDGE_FUNDAMENTALS,
    JUDGE_PROJECT_DEPTH,
    JUDGE_WEIGHTS,
)
from app.core.session_lookup import InterviewSessionNotFoundError
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.schemas.judge import JudgeEvidenceItem, JudgeOutput
from app.services.judge_service import (
    InterviewReportNotFoundError,
    InterviewSessionNotReadyForReportError,
    _apply_hint_penalty,
    _effective_weights,
    _tier_for_score,
    _transcript_slice_for_phases,
    generate_report,
    get_evaluations_by_ids,
    get_latest_report,
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


def _full_transcript() -> list[dict]:
    return [
        {"role": "user", "text": "hi"},
        {
            "role": "model",
            "text": "depth reply",
            "phase": "project_drill_down",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
        {
            "role": "model",
            "text": "coding reply",
            "phase": "coding_challenge",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
        {
            "role": "model",
            "text": "technical reply",
            "phase": "technical_interview",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
        {
            "role": "model",
            "text": "fundamentals reply",
            "phase": "general_technical",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
        {
            "role": "model",
            "text": "career reply",
            "phase": "career_motivation",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
        {
            "role": "model",
            "text": "questions reply",
            "phase": "candidate_questions",
            "hint_level": None,
            "red_flag": False,
            "severe_red_flag": False,
            "anxiety_detected": False,
        },
    ]


def _fake_session(**overrides) -> InterviewSession:
    defaults = {
        "id": 10,
        "candidate_profile_id": 1,
        "job_description_id": 2,
        "current_phase": "candidate_questions",
        "status": "completed",
        "transcript": _full_transcript(),
        "red_flag_count": 0,
        "red_flag_warning_issued": False,
        "hint_counts": {},
        "end_reason": None,
        "question_pool": [],
        "asked_question_ids": {},
        "github_call_count": 0,
    }
    defaults.update(overrides)
    return InterviewSession(**defaults)


def _judge_output(score: float) -> JudgeOutput:
    return JudgeOutput(
        score=score,
        summary="rationale",
        evidence=[JudgeEvidenceItem(quote="a quote", reasoning="why")],
    )


def _mock_db_for_report(
    mocker: MockerFixture, *, session: InterviewSession, job_description: JobDescription
) -> tuple[Any, list[Any]]:
    added: list[Any] = []
    next_id = {"value": 1}

    async def get(model, _id):
        if model is InterviewSession:
            return session
        if model is JobDescription:
            return job_description
        raise AssertionError(f"unexpected model {model}")

    def add(obj):
        added.append(obj)

    async def flush(*_args):
        for obj in added:
            if getattr(obj, "id", None) is None:
                obj.id = next_id["value"]
                next_id["value"] += 1

    fake_db = mocker.AsyncMock()
    fake_db.get = mocker.AsyncMock(side_effect=get)
    fake_db.add = mocker.MagicMock(side_effect=add)
    fake_db.flush = mocker.AsyncMock(side_effect=flush)
    fake_db.refresh = mocker.AsyncMock(side_effect=flush)
    fake_db.commit = mocker.AsyncMock()
    return fake_db, added


def _mock_generate_structured(mocker: MockerFixture, outputs: list[JudgeOutput]):
    return mocker.patch(
        "app.services.judge_service.generate_structured",
        new_callable=mocker.AsyncMock,
        side_effect=outputs,
    )


# --- pure function tests ---


def test_apply_hint_penalty_with_no_hints_is_unchanged() -> None:
    assert _apply_hint_penalty(80.0, {}) == 80.0


def test_apply_hint_penalty_single_level_one_hint() -> None:
    assert _apply_hint_penalty(100.0, {"technical_interview": 1}) == pytest.approx(95.0)


def test_apply_hint_penalty_cumulative_within_one_phase() -> None:
    # count=3 means levels 1+2+3 = 0.05+0.15+0.3 = 0.5 -> 50% off
    assert _apply_hint_penalty(100.0, {"technical_interview": 3}) == pytest.approx(50.0)


def test_apply_hint_penalty_combines_additively_across_phases() -> None:
    # level-1 in one phase (-5%) + level-1 in another phase (-5%) = -10%
    score = _apply_hint_penalty(
        100.0, {"technical_interview": 1, "general_technical": 1}
    )
    assert score == pytest.approx(90.0)


def test_apply_hint_penalty_clamps_to_zero_never_negative() -> None:
    score = _apply_hint_penalty(
        10.0, {"technical_interview": 3, "general_technical": 3, "coding_challenge": 3}
    )
    assert score == 0.0


def test_effective_weights_with_no_skip_matches_judge_weights() -> None:
    assert _effective_weights(set()) == JUDGE_WEIGHTS


def test_effective_weights_renormalizes_after_skipping_coding() -> None:
    weights = _effective_weights({JUDGE_CODING})

    assert JUDGE_CODING not in weights
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights[JUDGE_FUNDAMENTALS] == pytest.approx(
        JUDGE_WEIGHTS[JUDGE_FUNDAMENTALS] / 0.8
    )


@pytest.mark.parametrize(
    "score,expected_tier",
    [
        (85, "strong_hire"),
        (84.99, "hire"),
        (70, "hire"),
        (69.99, "borderline"),
        (55, "borderline"),
        (54.99, "no_hire"),
        (0, "no_hire"),
    ],
)
def test_tier_for_score_boundaries(score: float, expected_tier: str) -> None:
    assert _tier_for_score(score) == expected_tier


def test_transcript_slice_for_phases_none_returns_full_transcript() -> None:
    transcript = _full_transcript()
    assert _transcript_slice_for_phases(transcript, None) == transcript


def test_transcript_slice_for_phases_filters_by_phase() -> None:
    transcript = _full_transcript()
    sliced = _transcript_slice_for_phases(transcript, ["coding_challenge"])

    assert len(sliced) == 1
    assert sliced[0]["text"] == "coding reply"


def test_transcript_slice_for_phases_excludes_entries_missing_phase_key() -> None:
    transcript = [{"role": "user", "text": "no phase key here"}]
    assert _transcript_slice_for_phases(transcript, ["coding_challenge"]) == []


# --- generate_report() orchestration tests ---


async def test_generate_report_persists_all_five_evaluations_and_aggregates(
    mocker: MockerFixture,
) -> None:
    session = _fake_session()
    job_description = _fake_job_description()
    fake_db, added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    # order matches JUDGE_NAMES: project_depth, coding, fundamentals, attitude, career_fit
    _mock_generate_structured(
        mocker,
        [
            _judge_output(80),
            _judge_output(70),
            _judge_output(60),
            _judge_output(90),
            _judge_output(50),
        ],
    )

    report = await generate_report(session_id=10, db=fake_db)

    evaluation_judge_names = {e.judge_name for e in added if hasattr(e, "judge_name")}
    assert evaluation_judge_names == {
        JUDGE_PROJECT_DEPTH,
        JUDGE_CODING,
        JUDGE_FUNDAMENTALS,
        JUDGE_ATTITUDE,
        JUDGE_CAREER_FIT,
    }
    expected_overall = round(
        80 * JUDGE_WEIGHTS[JUDGE_PROJECT_DEPTH]
        + 70 * JUDGE_WEIGHTS[JUDGE_CODING]
        + 60 * JUDGE_WEIGHTS[JUDGE_FUNDAMENTALS]
        + 90 * JUDGE_WEIGHTS[JUDGE_ATTITUDE]
        + 50 * JUDGE_WEIGHTS[JUDGE_CAREER_FIT],
        2,
    )
    assert report.overall_score == pytest.approx(expected_overall)
    assert len(report.judge_evaluation_ids) == 5


async def test_generate_report_skips_coding_and_renormalizes_weights(
    mocker: MockerFixture,
) -> None:
    transcript = [e for e in _full_transcript() if e.get("phase") != "coding_challenge"]
    session = _fake_session(transcript=transcript)
    job_description = _fake_job_description(coding_assessment_expected=False)
    fake_db, added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    fake_generate = _mock_generate_structured(
        mocker,
        [_judge_output(80), _judge_output(60), _judge_output(90), _judge_output(50)],
    )

    report = await generate_report(session_id=10, db=fake_db)

    assert fake_generate.await_count == 4
    evaluation_judge_names = {e.judge_name for e in added if hasattr(e, "judge_name")}
    assert JUDGE_CODING not in evaluation_judge_names
    assert len(evaluation_judge_names) == 4
    assert report.weights_used[JUDGE_FUNDAMENTALS] == pytest.approx(
        JUDGE_WEIGHTS[JUDGE_FUNDAMENTALS] / 0.8
    )


async def test_generate_report_caps_attitude_score_on_abusive_language(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(end_reason="abusive_language", status="ended_early")
    job_description = _fake_job_description()
    fake_db, added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    _mock_generate_structured(
        mocker,
        [
            _judge_output(80),
            _judge_output(70),
            _judge_output(60),
            _judge_output(95),  # attitude's raw score, should be capped
            _judge_output(50),
        ],
    )

    await generate_report(session_id=10, db=fake_db)

    attitude_eval = next(
        e for e in added if getattr(e, "judge_name", None) == JUDGE_ATTITUDE
    )
    assert attitude_eval.score == ATTITUDE_ABUSIVE_LANGUAGE_SCORE_CAP


async def test_generate_report_does_not_cap_attitude_on_ordinary_red_flag_threshold(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(end_reason="red_flag_threshold", status="ended_early")
    job_description = _fake_job_description()
    fake_db, added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    _mock_generate_structured(
        mocker,
        [
            _judge_output(80),
            _judge_output(70),
            _judge_output(60),
            _judge_output(95),
            _judge_output(50),
        ],
    )

    await generate_report(session_id=10, db=fake_db)

    attitude_eval = next(
        e for e in added if getattr(e, "judge_name", None) == JUDGE_ATTITUDE
    )
    assert attitude_eval.score == 95.0


async def test_generate_report_applies_hint_penalty_to_attitude_score(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(hint_counts={"technical_interview": 1})
    job_description = _fake_job_description()
    fake_db, added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    _mock_generate_structured(
        mocker,
        [
            _judge_output(80),
            _judge_output(70),
            _judge_output(60),
            _judge_output(100),
            _judge_output(50),
        ],
    )

    await generate_report(session_id=10, db=fake_db)

    attitude_eval = next(
        e for e in added if getattr(e, "judge_name", None) == JUDGE_ATTITUDE
    )
    assert attitude_eval.score == pytest.approx(95.0)


async def test_generate_report_raises_when_session_in_progress(
    mocker: MockerFixture,
) -> None:
    session = _fake_session(status="in_progress")
    job_description = _fake_job_description()
    fake_db, _added = _mock_db_for_report(
        mocker, session=session, job_description=job_description
    )
    fake_generate = _mock_generate_structured(mocker, [])

    with pytest.raises(InterviewSessionNotReadyForReportError):
        await generate_report(session_id=10, db=fake_db)

    fake_generate.assert_not_awaited()


async def test_generate_report_raises_for_unknown_session(
    mocker: MockerFixture,
) -> None:
    fake_db = mocker.AsyncMock()
    fake_db.get = mocker.AsyncMock(return_value=None)

    with pytest.raises(InterviewSessionNotFoundError):
        await generate_report(session_id=999, db=fake_db)


# --- get_latest_report() / get_evaluations_by_ids() tests ---


async def test_get_latest_report_raises_when_none_exists(mocker: MockerFixture) -> None:
    session = _fake_session()
    fake_db = mocker.AsyncMock()
    fake_db.get = mocker.AsyncMock(return_value=session)
    fake_result = mocker.MagicMock()
    fake_result.scalar_one_or_none = mocker.MagicMock(return_value=None)
    fake_db.execute = mocker.AsyncMock(return_value=fake_result)

    with pytest.raises(InterviewReportNotFoundError):
        await get_latest_report(session_id=10, db=fake_db)


async def test_get_latest_report_returns_persisted_report(
    mocker: MockerFixture,
) -> None:
    session = _fake_session()
    fake_report = mocker.MagicMock()
    fake_db = mocker.AsyncMock()
    fake_db.get = mocker.AsyncMock(return_value=session)
    fake_result = mocker.MagicMock()
    fake_result.scalar_one_or_none = mocker.MagicMock(return_value=fake_report)
    fake_db.execute = mocker.AsyncMock(return_value=fake_result)

    report = await get_latest_report(session_id=10, db=fake_db)

    assert report is fake_report


async def test_get_evaluations_by_ids_returns_empty_list_without_querying(
    mocker: MockerFixture,
) -> None:
    fake_db = mocker.AsyncMock()
    fake_db.execute = mocker.AsyncMock()

    result = await get_evaluations_by_ids([], fake_db)

    assert result == []
    fake_db.execute.assert_not_awaited()


async def test_get_evaluations_by_ids_preserves_input_order(
    mocker: MockerFixture,
) -> None:
    eval_a = mocker.MagicMock(id=1)
    eval_b = mocker.MagicMock(id=2)
    fake_db = mocker.AsyncMock()
    fake_result = mocker.MagicMock()
    fake_result.scalars.return_value.all.return_value = [eval_b, eval_a]
    fake_db.execute = mocker.AsyncMock(return_value=fake_result)

    result = await get_evaluations_by_ids([1, 2], fake_db)

    assert result == [eval_a, eval_b]
