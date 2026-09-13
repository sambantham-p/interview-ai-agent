import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.models.interview_session import InterviewSession
from app.schemas.interview import (
    InterviewStartRequest,
    InterviewTurnRequest,
    InterviewTurnResponse,
)
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
    start_interview,
    submit_turn,
)

router = APIRouter(tags=["Interview"])


def _turn_response(session: InterviewSession) -> InterviewTurnResponse:
    return InterviewTurnResponse(
        id=session.id,
        current_phase=session.current_phase,
        status=session.status,
        red_flag_count=session.red_flag_count,
        hint_counts=session.hint_counts,
        end_reason=session.end_reason,
        reply=session.transcript[-1]["text"],
    )


@router.post("/interview/start", response_model=InterviewTurnResponse)
async def start(
    payload: InterviewStartRequest, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Create a new interview session for a candidate profile + job
    description pair, and generate the phase 1 opening message.
    """
    try:
        session = await start_interview(
            candidate_profile_id=payload.candidate_profile_id,
            job_description_id=payload.job_description_id,
            db=db,
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    return success_response(
        data=_turn_response(session), status_code=httpx.codes.CREATED
    )


@router.post("/interview/{session_id}/turn", response_model=InterviewTurnResponse)
async def turn(
    session_id: int,
    payload: InterviewTurnRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Submit one candidate turn and get the Interviewer agent's reply."""
    try:
        session = await submit_turn(
            session_id=session_id, message=payload.message, db=db
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InterviewSessionNotActiveError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.CONFLICT)

    return success_response(data=_turn_response(session), status_code=httpx.codes.OK)
