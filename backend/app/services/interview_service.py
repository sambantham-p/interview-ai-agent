from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.github import (
    GITHUB_CALL_BUDGET_PER_SESSION,
    GITHUB_TOOL_LOOP_MAX_ROUNDS,
)
from app.constants.interview import (
    DEFAULT_RED_FLAG_THRESHOLD,
    INTERVIEW_PHASES,
    LLM_TASK_INTERVIEWER,
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
from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.schemas.interview import InterviewTurnOutput
from app.services.interview_prompts import (
    ABUSIVE_LANGUAGE_ENDED_MESSAGE,
    INTERVIEW_ENDED_EARLY_MESSAGE,
    RED_FLAG_WARNING_MESSAGE,
    build_phase_system_instruction,
)
from app.services.question_bank_service import prefetch_question_pool

logger = structlog.get_logger(__name__)

__all__ = [
    "InterviewSessionNotActiveError",
    "InterviewSessionNotFoundError",
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


async def start_interview(
    *, candidate_profile_id: int, job_description_id: int, db: AsyncSession
) -> InterviewSession:
    """Create a new interview session and generate the opening message
    for phase 1 (Background Check).

    One fresh session per call, never a shared instance across
    candidates - each interview gets its own isolated state.
    """
    candidate_profile = await db.get(CandidateProfile, candidate_profile_id)
    if candidate_profile is None:
        raise InterviewSessionNotFoundError(
            f"No candidate profile with id {candidate_profile_id}"
        )
    job_description = await db.get(JobDescription, job_description_id)
    if job_description is None:
        raise InterviewSessionNotFoundError(
            f"No job description with id {job_description_id}"
        )

    session = InterviewSession(
        candidate_profile_id=candidate_profile_id,
        job_description_id=job_description_id,
        current_phase=INTERVIEW_PHASES[0],
    )
    db.add(session)
    await db.flush()

    session.question_pool = await prefetch_question_pool(
        job_description=job_description, db=db
    )

    # Prefetch once; reuse later instead of searching mid-turn.
    # Missing company_name skips research, and search failure must not block interview start.
    if job_description.company_name:
        try:
            session.company_research = await search_company_context(
                company_name=job_description.company_name,
                role=job_description.role,
            )
        except SearchTransientError:
            logger.warning(
                "interview.company_research.unavailable",
                company_name=job_description.company_name,
            )

    system_instruction = build_phase_system_instruction(
        session.current_phase, candidate_profile, job_description
    )
    opening_prompt_text = "Begin the interview - greet the candidate and start phase 1."
    output = await generate_structured(
        task=LLM_TASK_INTERVIEWER,
        contents=[types.Part.from_text(text=opening_prompt_text)],
        text_format=InterviewTurnOutput,
        system_instruction=system_instruction,
        thinking_level="medium",
        session_id=session.id,
        db=db,
    )

    session.transcript = [
        {"role": "user", "text": opening_prompt_text},
        {"role": "model", "text": output.reply, "phase": session.current_phase},
    ]
    await db.commit()
    await db.refresh(session)
    return session


async def submit_turn(
    *, session_id: int, message: str, db: AsyncSession
) -> InterviewSession:
    """Process one candidate turn: call the Interviewer agent with full
    conversation history, apply the agent's live judgment calls (hint
    level, red flag, phase transition), persist the updated session.
    """
    session = await get_interview_session_or_404(session_id, db)
    if session.status != "in_progress":
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
    system_instruction = build_phase_system_instruction(
        session.current_phase,
        candidate_profile,
        job_description,
        github_tools_available=github_tools_available,
        retrieved_questions=retrieved_questions,
        company_research=company_research,
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

    session = await get_interview_session_or_404(session_id, db, for_update=True)
    if session.status != "in_progress":
        raise InterviewSessionNotActiveError(
            f"Interview session {session_id} is {session.status}, not accepting turns"
        )
    session.github_call_count += github_calls_made

    reply = output.reply

    if output.severe_red_flag:
        session.red_flag_count += 1
        session.red_flag_warning_issued = True
        session.status = "ended_early"
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
            session.status = "ended_early"
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

    if session.status == "in_progress" and output.phase_complete:
        next_index = INTERVIEW_PHASES.index(session.current_phase) + 1
        if (
            next_index < len(INTERVIEW_PHASES)
            and INTERVIEW_PHASES[next_index] == "coding_challenge"
            and not job_description.coding_assessment_expected
        ):
            # JD doesn't call for a coding round just skip straight past it.
            next_index += 1
        if next_index < len(INTERVIEW_PHASES):
            session.current_phase = INTERVIEW_PHASES[next_index]
        else:
            session.status = "completed"
            session.ended_at = datetime.now(UTC)

    session.transcript = transcript
    await db.commit()
    await db.refresh(session)
    return session
