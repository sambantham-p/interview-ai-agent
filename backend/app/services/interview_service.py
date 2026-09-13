from datetime import UTC, datetime

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.interview import (
    DEFAULT_RED_FLAG_THRESHOLD,
    INTERVIEW_PHASES,
    LLM_TASK_INTERVIEWER,
)
from app.core.llm_gateway import generate_structured
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
        {"role": "model", "text": output.reply},
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

    transcript = [*session.transcript, {"role": "user", "text": message}]
    history = _transcript_to_history(transcript)
    system_instruction = build_phase_system_instruction(
        session.current_phase, candidate_profile, job_description
    )

    output = await generate_structured(
        task=LLM_TASK_INTERVIEWER,
        contents=history,
        text_format=InterviewTurnOutput,
        system_instruction=system_instruction,
        thinking_level="medium",
        session_id=session.id,
        db=db,
    )

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

    transcript.append({"role": "model", "text": reply})

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
