"""Resolves an interview preset + duration into the ordered phase list
and per-phase time budget stored on a session at interview-start.
"""

from datetime import datetime
from typing import Literal

from app.constants.interview import (
    CODING_PHASE,
    INTERVIEW_PHASES,
    INTERVIEW_PRESETS,
    PHASE_TIME_EXHAUSTED_FRACTION,
    PHASE_TIME_FORCE_COMPLETE_FRACTION,
    PHASE_TIME_LOW_FRACTION,
    PHASE_TIME_WEIGHTS,
)

PhaseTimeStatus = Literal["comfortable", "running_low", "exhausted"]


class InvalidInterviewPresetError(Exception):
    """Raised when a preset key, duration, or preset/JD combination
    can't produce a runnable interview.
    """


def resolve_phases(preset_key: str, *, coding_expected: bool) -> list[str]:
    """The preset's phases in INTERVIEW_PHASES order, with the coding
    phase dropped when the JD doesn't call for one.
    """
    preset = INTERVIEW_PRESETS.get(preset_key)
    if preset is None:
        raise InvalidInterviewPresetError(f"Unknown interview preset '{preset_key}'")

    wanted = set(preset["phases"])
    phases = [p for p in INTERVIEW_PHASES if p in wanted]
    if not coding_expected:
        phases = [p for p in phases if p != CODING_PHASE]
    if not phases:
        raise InvalidInterviewPresetError(
            f"The '{preset_key}' preset needs a coding round, but this job "
            "description doesn't call for one"
        )
    return phases


def split_time_budget(phases: list[str], duration_minutes: int) -> dict[str, int]:
    """Splits `duration_minutes` across `phases` in whole minutes,
    proportional to PHASE_TIME_WEIGHTS. The budgets always add up to
    exactly `duration_minutes`.

    Each share is rounded down, then the minutes left over go one each to
    the phases with the largest fractional part (largest-remainder
    method), so no minute is lost or invented.
    """
    if not phases or duration_minutes <= 0:
        raise ValueError("Need at least one phase and a positive duration")
    missing = [p for p in phases if PHASE_TIME_WEIGHTS.get(p, 0) <= 0]
    if missing:
        raise ValueError(f"No positive time weight configured for {missing}")

    total_weight = sum(PHASE_TIME_WEIGHTS[p] for p in phases)
    shares = {
        p: duration_minutes * PHASE_TIME_WEIGHTS[p] / total_weight for p in phases
    }
    budget = {p: int(share) for p, share in shares.items()}

    leftover = duration_minutes - sum(budget.values())
    by_largest_fraction = sorted(
        phases, key=lambda p: shares[p] - budget[p], reverse=True
    )
    for p in by_largest_fraction[:leftover]:
        budget[p] += 1

    if sum(budget.values()) != duration_minutes:
        raise RuntimeError(
            f"Phase budgets {budget} don't add up to {duration_minutes} minutes"
        )
    return budget


def build_session_plan(
    *, preset_key: str, duration_minutes: int, coding_expected: bool
) -> tuple[list[str], dict[str, int]]:
    """Validate the preset/duration pair and return (phases, budget)."""
    phases = resolve_phases(preset_key, coding_expected=coding_expected)
    allowed = INTERVIEW_PRESETS[preset_key]["durations"]
    if duration_minutes not in allowed:
        raise InvalidInterviewPresetError(
            f"The '{preset_key}' preset runs for {allowed} minutes, "
            f"not {duration_minutes}"
        )
    return phases, split_time_budget(phases, duration_minutes)


def phase_time_status(
    *, budget_minutes: float, phase_started_at: datetime, now: datetime
) -> tuple[PhaseTimeStatus, bool]:
    """(status, force_complete) for the current phase's elapsed time.

    force_complete is the server-side safety valve for a phase that
    overran its budget by a wide margin despite the wrap-up instruction.
    """
    elapsed = (now - phase_started_at).total_seconds() / 60
    fraction = elapsed / budget_minutes
    if fraction >= PHASE_TIME_EXHAUSTED_FRACTION:
        status: PhaseTimeStatus = "exhausted"
    elif fraction >= PHASE_TIME_LOW_FRACTION:
        status = "running_low"
    else:
        status = "comfortable"
    return status, fraction >= PHASE_TIME_FORCE_COMPLETE_FRACTION
