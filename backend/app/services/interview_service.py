import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.github import (
    GITHUB_CALL_BUDGET_PER_SESSION,
    GITHUB_TOOL_LOOP_MAX_ROUNDS,
)
from app.constants.interview import (
    CODING_PHASE,
    DEFAULT_RED_FLAG_THRESHOLD,
    INTERVIEW_PHASES,
    INTERVIEW_PRESETS,
    LLM_TASK_INTERVIEWER,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_ENDED_EARLY,
    SESSION_STATUS_IN_PROGRESS,
)
from app.constants.question_bank import QUESTION_BANK_PHASES, QUESTIONS_PER_PHASE
from app.constants.search import COMPANY_RESEARCH_PHASES
from app.core.github_client import extract_github_username
from app.core.github_tools import GITHUB_TOOLS, build_scoped_github_dispatch
from app.core.llm_gateway import generate_structured, generate_structured_with_tools
from app.core.search_mcp_client import SearchTransientError, search_company_context
from app.core.session_lookup import (
    InterviewSessionNotFoundError,
    get_interview_session_or_404,
)
from app.dto.interview import InterviewTurnOutput
from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.services.interview_presets import (
    InvalidInterviewPresetError,
    build_session_plan,
    phase_time_status,
)
from app.services.interview_prompts import (
    ABUSIVE_LANGUAGE_ENDED_MESSAGE,
    INTERVIEW_ENDED_EARLY_MESSAGE,
    RED_FLAG_WARNING_MESSAGE,
    build_phase_system_instruction,
)
from app.services.question_bank_service import prefetch_question_pool

logger = structlog.get_logger(__name__)

OPENING_PROMPT_TEXT = (
    "Begin the interview - greet the candidate and start the first phase."
)

__all__ = [
    "InterviewSessionNotActiveError",
    "InterviewSessionNotFoundError",
    "InvalidInterviewPresetError",
    "list_interview_presets",
    "start_interview",
    "submit_turn",
]


def _transcript_to_history(transcript: list[dict]) -> list[types.Content]:
    return [
        types.Content(
            role=entry["role"], parts=[types.Part.from_text(text=entry["text"])]
        )
        for entry in transcript
    ]


class InterviewSessionNotActiveError(Exception):
    """Raised when a turn is submitted to a session that already
    completed or ended early - no further turns are accepted.
    """


def list_interview_presets(*, coding_expected: bool | None = None) -> list[dict]:
    """The preset catalog; with coding_expected=False, presets that
    include the coding phase are left out rather than offered and later
    silently trimmed.
    """
    presets = []
    for key, preset in INTERVIEW_PRESETS.items():
        includes_coding = CODING_PHASE in preset["phases"]
        if coding_expected is False and includes_coding:
            continue
        presets.append({"key": key, **preset, "includes_coding": includes_coding})
    return presets


def _phase_sequence(
    session: InterviewSession, job_description: JobDescription
) -> list[str]:
    """The ordered phases this session walks. Sessions started without a
    preset fall back to every phase, skipping coding when the JD doesn't
    call for it.
    """
    if session.selected_phases:
        return list(session.selected_phases)
    return [
        p
        for p in INTERVIEW_PHASES
        if p != CODING_PHASE or job_description.coding_assessment_expected
    ]


def _current_phase_time_status(
    session: InterviewSession, now: datetime
) -> tuple[str | None, bool]:
    """(time_status, force_complete) for the current phase, or
    (None, False) when the session has no time budget.
    """
    budget = (session.phase_time_budget or {}).get(session.current_phase)
    if not budget or session.phase_started_at is None:
        return None, False
    return phase_time_status(
        budget_minutes=budget, phase_started_at=session.phase_started_at, now=now
    )


def _questions_for_phase(session: InterviewSession) -> list[str]:
    """Selects up to QUESTIONS_PER_PHASE pool entries for the current
    phase, deduped across phases 3/4/5 sharing one pool.

    Selected once per phase, not once per turn: a phase already holding a
    batch (asked_question_ids[phase]) reoffers that same batch on every
    later turn instead of picking fresh ones, or a multi-turn phase would
    burn through the whole pool before reaching the next phase.
    """
    phase = session.current_phase
    asked_by_phase = dict(session.asked_question_ids)

    if phase in asked_by_phase:
        already_offered_ids = set(asked_by_phase[phase])
        return [
            q["question_text"]
            for q in session.question_pool
            if q["id"] in already_offered_ids
        ]

    used_elsewhere = {qid for ids in asked_by_phase.values() for qid in ids}
    unused = [q for q in session.question_pool if q["id"] not in used_elsewhere]
    selected = unused[:QUESTIONS_PER_PHASE]
    if selected:
        asked_by_phase[phase] = [q["id"] for q in selected]
        session.asked_question_ids = asked_by_phase
    return [q["question_text"] for q in selected]


def _counting_dispatch(
    dispatch: dict[str, Callable[..., Awaitable[Any]]], counter: list[int]
) -> dict[str, Callable[..., Awaitable[Any]]]:
    """Wraps a tool_dispatch table so every call increments `counter[0]` -
    lets submit_turn() count actual GitHub calls made this turn, to add
    onto session.github_call_count afterwards.
    """

    def _wrap(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        async def wrapped(**kwargs: Any) -> Any:
            counter[0] += 1
            return await fn(**kwargs)

        return wrapped

    return {name: _wrap(fn) for name, fn in dispatch.items()}


async def _prefetch_company_research(job_description: JobDescription) -> str | None:
    """Company research for phases 6/7, fetched once at interview start.
    A missing company name skips it, and a search failure never blocks the
    interview from starting.
    """
    if not job_description.company_name:
        return None
    try:
        return await search_company_context(
            company_name=job_description.company_name,
            role=job_description.role,
        )
    except SearchTransientError:
        logger.warning(
            "interview.company_research.unavailable",
            company_name=job_description.company_name,
        )
        return None


async def _generate_opening(
    session: InterviewSession,
    candidate_profile: CandidateProfile,
    job_description: JobDescription,
    db: AsyncSession,
) -> InterviewTurnOutput:
    """Prefetch the question pool and company research (independent, so
    concurrently), then generate the interviewer's opening message.
    """
    session.question_pool, session.company_research = await asyncio.gather(
        prefetch_question_pool(job_description=job_description, db=db),
        _prefetch_company_research(job_description),
    )

    system_instruction = build_phase_system_instruction(
        session.current_phase, candidate_profile, job_description
    )
    return await generate_structured(
        task=LLM_TASK_INTERVIEWER,
        contents=[types.Part.from_text(text=OPENING_PROMPT_TEXT)],
        text_format=InterviewTurnOutput,
        system_instruction=system_instruction,
        thinking_level="medium",
        session_id=session.id,
        db=db,
    )


async def start_interview(
    *,
    candidate_profile_id: int,
    job_description_id: int,
    user_id: str,
    db: AsyncSession,
    preset_key: str | None = None,
    duration_minutes: int | None = None,
) -> InterviewSession:
    """Create a new interview session and generate the opening message
    for its first phase.

    With a preset, the session walks that preset's phases and gets a
    per-phase time budget; without one it runs every phase, untimed.

    One fresh session per call, never a shared instance across
    candidates - each interview gets its own isolated state.

    Both the candidate profile and job description must belong to
    `user_id` - a mismatch raises the same not-found error as a missing
    id, so this can't be used to probe another user's profile/JD ids
    (same IDOR-safe pattern as get_interview_session_or_404).
    """
    candidate_profile = await db.get(CandidateProfile, candidate_profile_id)
    if candidate_profile is None or candidate_profile.user_id != user_id:
        raise InterviewSessionNotFoundError(
            f"No candidate profile with id {candidate_profile_id}"
        )
    job_description = await db.get(JobDescription, job_description_id)
    if job_description is None or job_description.user_id != user_id:
        raise InterviewSessionNotFoundError(
            f"No job description with id {job_description_id}"
        )

    selected_phases: list[str] = []
    phase_budget: dict[str, float] = {}
    if preset_key is not None and duration_minutes is not None:
        selected_phases, phase_budget = build_session_plan(
            preset_key=preset_key,
            duration_minutes=duration_minutes,
            coding_expected=job_description.coding_assessment_expected,
        )

    session = InterviewSession(
        user_id=user_id,
        candidate_profile_id=candidate_profile_id,
        job_description_id=job_description_id,
        current_phase=(selected_phases or INTERVIEW_PHASES)[0],
        selected_phases=selected_phases,
        duration_minutes=duration_minutes,
        phase_time_budget=phase_budget,
        phase_started_at=datetime.now(UTC),
    )
    db.add(session)
    # Committed before any LLM call: the Gateway logs each call on its own
    # connection, and that log row references this session by foreign key,
    # so an uncommitted session would make every logged call fail.
    await db.commit()

    try:
        output = await _generate_opening(
            session, candidate_profile, job_description, db
        )
    except Exception:
        await db.delete(session)
        await db.commit()
        raise

    session.transcript = [
        {"role": "user", "text": OPENING_PROMPT_TEXT},
        {"role": "model", "text": output.reply, "phase": session.current_phase},
    ]
    await db.commit()
    await db.refresh(session)
    return session


async def submit_turn(
    *, session_id: int, message: str, user_id: str, db: AsyncSession
) -> InterviewSession:
    """Process one candidate turn: call the Interviewer agent with full
    conversation history, apply the agent's live judgment calls (hint
    level, red flag, phase transition), persist the updated session.
    """
    session = await get_interview_session_or_404(
        session_id, db, user_id=user_id, for_update=True
    )
    if session.status != SESSION_STATUS_IN_PROGRESS:
        raise InterviewSessionNotActiveError(
            f"Interview session {session_id} is {session.status}, not accepting turns"
        )

    candidate_profile = await db.get(CandidateProfile, session.candidate_profile_id)
    job_description = await db.get(JobDescription, session.job_description_id)
    assert candidate_profile is not None  # nosec B101
    assert job_description is not None  # nosec B101

    transcript = [
        *session.transcript,
        {"role": "user", "text": message, "phase": session.current_phase},
    ]
    history = _transcript_to_history(transcript)
    candidate_username = extract_github_username(candidate_profile.github_url)
    github_tools_available = (
        session.current_phase == "project_drill_down"
        and candidate_username is not None
        and session.github_call_count < GITHUB_CALL_BUDGET_PER_SESSION
    )
    retrieved_questions = (
        _questions_for_phase(session)
        if session.current_phase in QUESTION_BANK_PHASES
        else None
    )
    company_research = (
        session.company_research
        if session.current_phase in COMPANY_RESEARCH_PHASES
        else None
    )
    time_status, force_complete = _current_phase_time_status(session, datetime.now(UTC))
    system_instruction = build_phase_system_instruction(
        session.current_phase,
        candidate_profile,
        job_description,
        github_tools_available=github_tools_available,
        retrieved_questions=retrieved_questions,
        company_research=company_research,
        time_status=time_status,
    )

    if github_tools_available:
        call_counter = [0]
        assert candidate_username is not None  # nosec B101 - checked above
        output = await generate_structured_with_tools(
            task=LLM_TASK_INTERVIEWER,
            contents=history,
            text_format=InterviewTurnOutput,
            system_instruction=system_instruction,
            thinking_level="medium",
            tools=GITHUB_TOOLS,
            tool_dispatch=_counting_dispatch(
                build_scoped_github_dispatch(candidate_username), call_counter
            ),
            max_rounds=GITHUB_TOOL_LOOP_MAX_ROUNDS,
            session_id=session.id,
            db=db,
        )
        github_calls_made = call_counter[0]
    else:
        output = await generate_structured(
            task=LLM_TASK_INTERVIEWER,
            contents=history,
            text_format=InterviewTurnOutput,
            system_instruction=system_instruction,
            thinking_level="medium",
            session_id=session.id,
            db=db,
        )
        github_calls_made = 0

    session.github_call_count += github_calls_made

    reply = output.reply

    if output.severe_red_flag:
        session.red_flag_count += 1
        session.red_flag_warning_issued = True
        session.status = SESSION_STATUS_ENDED_EARLY
        session.ended_at = datetime.now(UTC)
        session.end_reason = "abusive_language"
        reply = f"{reply}\n\n{ABUSIVE_LANGUAGE_ENDED_MESSAGE}"
    elif output.red_flag:
        session.red_flag_count += 1
        if (
            session.red_flag_count >= DEFAULT_RED_FLAG_THRESHOLD
            and not session.red_flag_warning_issued
        ):
            session.red_flag_warning_issued = True
            reply = f"{reply}\n\n{RED_FLAG_WARNING_MESSAGE}"
        elif (
            session.red_flag_count > DEFAULT_RED_FLAG_THRESHOLD
            and session.red_flag_warning_issued
        ):
            session.status = SESSION_STATUS_ENDED_EARLY
            session.ended_at = datetime.now(UTC)
            session.end_reason = "red_flag_threshold"
            reply = f"{reply}\n\n{INTERVIEW_ENDED_EARLY_MESSAGE}"

    if output.hint_level is not None:
        # Per-phase counter; hints in one phase do not affect escalation in another.
        hint_counts = dict(session.hint_counts)
        hint_counts[session.current_phase] = (
            hint_counts.get(session.current_phase, 0) + 1
        )
        session.hint_counts = hint_counts

    transcript.append(
        {
            "role": "model",
            "text": reply,
            "phase": session.current_phase,
            "hint_level": output.hint_level,
            "red_flag": output.red_flag,
            "severe_red_flag": output.severe_red_flag,
            "anxiety_detected": output.anxiety_detected,
        }
    )

    if session.status == SESSION_STATUS_IN_PROGRESS and (
        output.phase_complete or force_complete
    ):
        phases = _phase_sequence(session, job_description)
        next_index = phases.index(session.current_phase) + 1
        if next_index < len(phases):
            session.current_phase = phases[next_index]
            session.phase_started_at = datetime.now(UTC)
        else:
            session.status = SESSION_STATUS_COMPLETED
            session.ended_at = datetime.now(UTC)

    session.transcript = transcript
    await db.commit()
    await db.refresh(session)
    return session


async def list_interview_sessions(
    user_id: str, db: AsyncSession
) -> list[InterviewSession]:
    """Every interview session the given user has started, newest first -
    powers the dashboard's recent-interviews list and the documents page.
    """
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.created_at.desc())
    )
    return list(result.scalars().all())
