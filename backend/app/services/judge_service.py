"""Post-hoc Judge agents (PoLL pattern: 5 independent scorers, no
cross-judge debate) and the aggregated report they produce.

Judges only run over a session's finished transcript, never live during
the interview itself - see interview_service.py for the live turn loop.
"""

from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.interview import HINT_PENALTY_BY_LEVEL
from app.constants.judge import (
    ATTITUDE_ABUSIVE_LANGUAGE_SCORE_CAP,
    JUDGE_ATTITUDE,
    JUDGE_CAREER_FIT,
    JUDGE_CODING,
    JUDGE_FUNDAMENTALS,
    JUDGE_NAMES,
    JUDGE_PHASES,
    JUDGE_PROJECT_DEPTH,
    JUDGE_WEIGHTS,
    LLM_TASK_JUDGE_ATTITUDE,
    LLM_TASK_JUDGE_CAREER_FIT,
    LLM_TASK_JUDGE_CODING,
    LLM_TASK_JUDGE_FUNDAMENTALS,
    LLM_TASK_JUDGE_PROJECT_DEPTH,
    RECOMMENDATION_TIERS,
)
from app.core.llm_gateway import generate_structured
from app.models.interview_report import InterviewReport
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.models.judge_evaluation import JudgeEvaluation
from app.schemas.judge import JudgeOutput
from app.services.judge_prompts import (
    ATTITUDE_INSTRUCTIONS,
    CAREER_FIT_INSTRUCTIONS,
    CODING_INSTRUCTIONS,
    FUNDAMENTALS_INSTRUCTIONS,
    PROJECT_DEPTH_INSTRUCTIONS,
    build_attitude_context,
    build_judge_system_instruction,
)

__all__ = [
    "InterviewReportNotFoundError",
    "InterviewSessionNotReadyForReportError",
    "generate_report",
    "get_evaluations_by_ids",
    "get_latest_report",
]

_JUDGE_TASK_BY_NAME = {
    JUDGE_PROJECT_DEPTH: LLM_TASK_JUDGE_PROJECT_DEPTH,
    JUDGE_CODING: LLM_TASK_JUDGE_CODING,
    JUDGE_FUNDAMENTALS: LLM_TASK_JUDGE_FUNDAMENTALS,
    JUDGE_ATTITUDE: LLM_TASK_JUDGE_ATTITUDE,
    JUDGE_CAREER_FIT: LLM_TASK_JUDGE_CAREER_FIT,
}

_JUDGE_INSTRUCTIONS_BY_NAME = {
    JUDGE_PROJECT_DEPTH: PROJECT_DEPTH_INSTRUCTIONS,
    JUDGE_CODING: CODING_INSTRUCTIONS,
    JUDGE_FUNDAMENTALS: FUNDAMENTALS_INSTRUCTIONS,
    JUDGE_ATTITUDE: ATTITUDE_INSTRUCTIONS,
    JUDGE_CAREER_FIT: CAREER_FIT_INSTRUCTIONS,
}

_JUDGE_DIMENSION_LABEL = {
    JUDGE_PROJECT_DEPTH: "Project Depth",
    JUDGE_CODING: "Coding",
    JUDGE_FUNDAMENTALS: "Technical Fundamentals",
    JUDGE_ATTITUDE: "Attitude & Communication",
    JUDGE_CAREER_FIT: "Career Fit",
}


class InterviewSessionNotReadyForReportError(Exception):
    """Raised when report generation is requested for a session that's
    still "in_progress" - a report needs a finished transcript
    ("completed" or "ended_early" are both acceptable, see
    generate_report()).
    """


class InterviewReportNotFoundError(Exception):
    """Raised when a report is requested for a session with none
    generated yet.
    """


def _transcript_slice_for_phases(
    transcript: list[dict], phases: list[str] | None
) -> list[dict]:
    """Filters transcript entries to only those whose "phase" key (tagged
    on the model reply by interview_service.py) is in `phases`. `phases
    is None` returns the full transcript unchanged - used by the
    cross-cutting Attitude judge. An old-shape entry with no "phase" key
    (from before transcript enrichment, or any "role": "user" entry) is
    excluded rather than raising.
    """
    if phases is None:
        return transcript
    return [entry for entry in transcript if entry.get("phase") in phases]


def _transcript_to_contents(transcript: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role=entry["role"], parts=[types.Part.from_text(text=entry["text"])]
        )
        for entry in transcript
    ]


def _job_description_summary(job_description: JobDescription) -> str:
    return (
        f"Job description: role={job_description.role!r}, "
        f"seniority={job_description.seniority!r}, "
        f"tech_stack={job_description.tech_stack!r}."
    )


def _apply_hint_penalty(score: float, hint_counts: dict[str, int]) -> float:
    """Deterministic penalty, not LLM-computed - keeps the exact
    HINT_PENALTY_BY_LEVEL arithmetic auditable and testable without
    mocking an LLM call. hint_counts is keyed by phase with a single
    cumulative count per phase (not a level breakdown), so each phase's
    count is treated as having reached that many escalation steps and
    charged the corresponding cumulative penalty fraction.
    """
    total_penalty_fraction = 0.0
    for count in hint_counts.values():
        for level in range(1, min(count, len(HINT_PENALTY_BY_LEVEL)) + 1):
            total_penalty_fraction += HINT_PENALTY_BY_LEVEL[level]
    penalized = score * (1 - min(total_penalty_fraction, 1.0))
    return max(0.0, penalized)


def _effective_weights(skipped_judges: set[str]) -> dict[str, float]:
    """Renormalizes JUDGE_WEIGHTS to sum to 1.0 after excluding any
    skipped judges (e.g. Coding when coding_assessment_expected=False, or
    any judge with no material transcript segment) instead of scoring a
    skipped dimension as 0 or crashing on a missing evaluation.
    """
    remaining = {
        name: weight
        for name, weight in JUDGE_WEIGHTS.items()
        if name not in skipped_judges
    }
    total = sum(remaining.values())
    return {name: weight / total for name, weight in remaining.items()}


def _tier_for_score(score: float) -> str:
    for threshold, tier in RECOMMENDATION_TIERS:
        if score >= threshold:
            return tier
    return RECOMMENDATION_TIERS[-1][1]


async def _run_judge(
    *,
    judge_name: str,
    session: InterviewSession,
    job_description: JobDescription,
    db: AsyncSession,
) -> JudgeEvaluation | None:
    """Runs one Judge agent. Returns None (skip) if this judge's phase(s)
    have no transcript entries - e.g. coding_challenge was skipped for
    this JD, or an ended_early session never reached this phase.
    """
    phases = JUDGE_PHASES[judge_name]
    segment = _transcript_slice_for_phases(session.transcript, phases)
    if phases is not None and not segment:
        return None

    extra_context = None
    if judge_name == JUDGE_ATTITUDE:
        extra_context = build_attitude_context(
            red_flag_count=session.red_flag_count,
            severe_red_flag=session.end_reason == "abusive_language",
            hint_counts=session.hint_counts,
        )
        segment = session.transcript  # cross-cutting: full transcript

    system_instruction = build_judge_system_instruction(
        _JUDGE_INSTRUCTIONS_BY_NAME[judge_name],
        job_description_summary=_job_description_summary(job_description),
        extra_context=extra_context,
    )

    output = await generate_structured(
        task=_JUDGE_TASK_BY_NAME[judge_name],
        contents=_transcript_to_contents(segment),
        text_format=JudgeOutput,
        system_instruction=system_instruction,
        thinking_level="medium",
        session_id=session.id,
        db=db,
    )

    score = output.score
    if judge_name == JUDGE_ATTITUDE:
        score = _apply_hint_penalty(score, session.hint_counts)
        if session.end_reason == "abusive_language":
            score = min(score, ATTITUDE_ABUSIVE_LANGUAGE_SCORE_CAP)

    evaluation = JudgeEvaluation(
        session_id=session.id,
        judge_name=judge_name,
        dimension=_JUDGE_DIMENSION_LABEL[judge_name],
        score=round(score, 2),
        summary=output.summary,
        evidence=[item.model_dump() for item in output.evidence],
    )
    db.add(evaluation)
    await db.flush()
    return evaluation


async def generate_report(
    *, session: InterviewSession, db: AsyncSession
) -> InterviewReport:
    """Runs all 5 Judges sequentially (db is a single request-scoped
    AsyncSession, not safe for concurrent Gateway calls), persists each
    JudgeEvaluation, then aggregates into a new InterviewReport row.

    Allowed for "completed" and "ended_early" sessions - an interview
    ended early for a red-flag threshold or abusive language still needs
    an evaluation report, with that context reflected in the Attitude
    judge's score (see _run_judge).

    Takes an already-fetched, ownership-verified session rather than a
    session_id - the caller (app/routes/interview.py) already needs the
    session object itself to build the response, so fetching it a second
    time here would be a redundant round-trip.
    """
    if session.status not in ("completed", "ended_early"):
        raise InterviewSessionNotReadyForReportError(
            f"Interview session {session.id} is {session.status}, not ready for a report"
        )

    job_description = await db.get(JobDescription, session.job_description_id)
    assert job_description is not None  # nosec B101

    evaluations: list[JudgeEvaluation] = []
    skipped: set[str] = set()
    for judge_name in JUDGE_NAMES:
        evaluation = await _run_judge(
            judge_name=judge_name,
            session=session,
            job_description=job_description,
            db=db,
        )
        if evaluation is None:
            skipped.add(judge_name)
        else:
            evaluations.append(evaluation)

    weights = _effective_weights(skipped)
    overall_score = round(
        sum(float(e.score) * weights[e.judge_name] for e in evaluations), 2
    )

    report = InterviewReport(
        session_id=session.id,
        overall_score=overall_score,
        recommendation_tier=_tier_for_score(overall_score),
        weights_used=weights,
        judge_evaluation_ids=[e.id for e in evaluations],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def get_latest_report(
    *, session: InterviewSession, db: AsyncSession
) -> InterviewReport:
    """Fetches the most recently generated report for a session without
    re-running any Judges.

    Takes an already-fetched, ownership-verified session - see
    generate_report()'s docstring for why.
    """
    result = await db.execute(
        select(InterviewReport)
        .where(InterviewReport.session_id == session.id)
        .order_by(InterviewReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise InterviewReportNotFoundError(
            f"No report generated yet for interview session {session.id}"
        )
    return report


async def get_evaluations_by_ids(
    ids: list[int], db: AsyncSession
) -> list[JudgeEvaluation]:
    """Fetches JudgeEvaluation rows by id, preserving the report's
    judge_evaluation_ids order - used by the route layer to build the
    full report response without re-running any Judges.
    """
    if not ids:
        return []
    result = await db.execute(
        select(JudgeEvaluation).where(JudgeEvaluation.id.in_(ids))
    )
    by_id = {e.id: e for e in result.scalars().all()}
    return [by_id[i] for i in ids if i in by_id]
