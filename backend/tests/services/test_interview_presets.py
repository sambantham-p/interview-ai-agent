from datetime import UTC, datetime, timedelta

import pytest

from app.constants.interview import (
    INTERVIEW_PHASES,
    INTERVIEW_PRESETS,
)
from app.services.interview_presets import (
    InvalidInterviewPresetError,
    build_session_plan,
    max_answer_seconds,
    phase_time_status,
    resolve_phases,
    split_time_budget,
)


def test_every_preset_is_an_ordered_subset_of_interview_phases() -> None:
    for preset in INTERVIEW_PRESETS.values():
        indexes = [INTERVIEW_PHASES.index(p) for p in preset["phases"]]
        assert indexes == sorted(indexes)


def test_resolve_phases_keeps_interview_phases_order() -> None:
    assert resolve_phases("technical_round", coding_expected=True) == [
        "technical_interview",
        "coding_challenge",
        "general_technical",
    ]


def test_resolve_phases_drops_coding_when_jd_does_not_expect_it() -> None:
    phases = resolve_phases("project_coding_combo", coding_expected=False)

    assert phases == ["project_drill_down"]


def test_resolve_phases_rejects_a_coding_only_preset_without_coding() -> None:
    with pytest.raises(InvalidInterviewPresetError, match="coding round"):
        resolve_phases("coding_only", coding_expected=False)


def test_resolve_phases_rejects_unknown_preset() -> None:
    with pytest.raises(InvalidInterviewPresetError, match="Unknown"):
        resolve_phases("nope", coding_expected=True)


def test_split_time_budget_weights_phases() -> None:
    budget = split_time_budget(INTERVIEW_PHASES, 30)

    assert budget["project_drill_down"] > budget["background_check"]
    assert budget["general_technical"] > budget["career_motivation"]


def test_split_time_budget_gives_whole_minutes() -> None:
    budget = split_time_budget(INTERVIEW_PHASES, 30)

    assert all(isinstance(v, int) for v in budget.values())


def test_every_preset_and_duration_adds_up_to_exactly_the_chosen_minutes() -> None:
    for key, preset in INTERVIEW_PRESETS.items():
        for coding_expected in (True, False):
            try:
                phases = resolve_phases(key, coding_expected=coding_expected)
            except InvalidInterviewPresetError:
                continue
            for duration in preset["durations"]:
                budget = split_time_budget(phases, duration)
                assert sum(budget.values()) == duration, (key, duration, budget)
                # A 0-minute phase would silently disable its time tracking.
                assert all(v >= 1 for v in budget.values()), (key, duration, budget)


def test_split_time_budget_is_purely_proportional_to_weights() -> None:
    # weights project 3 : general 2 : career 1 -> 30 minutes = 15 / 10 / 5
    budget = split_time_budget(
        ["project_drill_down", "general_technical", "career_motivation"], 30
    )

    assert budget == {
        "project_drill_down": 15,
        "general_technical": 10,
        "career_motivation": 5,
    }


def test_split_time_budget_hands_leftover_minutes_to_the_largest_remainders() -> None:
    # weights 3:3:1 over 10 minutes = 4.29 / 4.29 / 1.43 -> floors 4 / 4 / 1
    # leave one minute over, which goes to the largest fraction (1.43).
    budget = split_time_budget(
        ["project_drill_down", "technical_interview", "candidate_questions"], 10
    )

    assert budget == {
        "project_drill_down": 4,
        "technical_interview": 4,
        "candidate_questions": 2,
    }


def test_split_time_budget_single_phase_gets_everything() -> None:
    assert split_time_budget(["coding_challenge"], 10) == {"coding_challenge": 10}


@pytest.mark.parametrize(
    ("phases", "duration"),
    [([], 10), (["coding_challenge"], 0), (["coding_challenge"], -5)],
)
def test_split_time_budget_rejects_empty_phases_or_non_positive_duration(
    phases: list[str], duration: int
) -> None:
    with pytest.raises(ValueError, match="positive duration"):
        split_time_budget(phases, duration)


def test_split_time_budget_rejects_phase_without_a_positive_weight() -> None:
    with pytest.raises(ValueError, match="time weight"):
        split_time_budget(["not_a_phase"], 10)


def test_build_session_plan_rejects_duration_outside_preset() -> None:
    with pytest.raises(InvalidInterviewPresetError, match="minutes"):
        build_session_plan(
            preset_key="coding_only", duration_minutes=40, coding_expected=True
        )


def test_build_session_plan_returns_phases_and_budget() -> None:
    phases, budget = build_session_plan(
        preset_key="full_loop", duration_minutes=30, coding_expected=False
    )

    assert "coding_challenge" not in phases
    assert set(budget) == set(phases)
    assert sum(budget.values()) == 30


@pytest.mark.parametrize(
    ("elapsed_minutes", "expected", "force"),
    [
        (1, "comfortable", False),
        (4, "running_low", False),
        (6, "exhausted", False),
        (8, "exhausted", True),
    ],
)
def test_phase_time_status_thresholds(
    elapsed_minutes: float, expected: str, force: bool
) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)

    status, force_complete = phase_time_status(
        budget_minutes=5,
        phase_started_at=now - timedelta(minutes=elapsed_minutes),
        now=now,
    )

    assert (status, force_complete) == (expected, force)


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(None, 300), (5, 180), (20, 300), (40, 480), (120, 480)],
)
def test_max_answer_seconds_scales_with_duration_within_bounds(
    duration: int | None, expected: int
) -> None:
    assert max_answer_seconds(duration) == expected


def test_split_time_budget_raises_if_budgets_do_not_sum_to_the_duration(
    mocker,
) -> None:
    # With no leftover minute handed out, the whole-minute floors fall short.
    mocker.patch("app.services.interview_presets.sorted", return_value=[], create=True)

    with pytest.raises(RuntimeError, match="don't add up"):
        split_time_budget(["technical_interview", "career_motivation"], 7)
