import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.core.session_lookup import get_interview_session_or_404
from app.dto.interview import (
    InterviewPresetResponse,
    InterviewSessionSummary,
    InterviewStartRequest,
    InterviewTurnRequest,
    InterviewTurnResponse,
    build_turn_response,
)
from app.dto.judge import InterviewReportResponse
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
    InvalidInterviewPresetError,
    list_interview_presets,
    list_interview_sessions,
    start_interview,
    submit_turn,
)
from app.services.judge_service import (
    InterviewReportNotFoundError,
    InterviewSessionNotReadyForReportError,
    generate_report,
    get_latest_report,
    get_report_evaluations,
)

router = APIRouter(tags=["Interview"])


@router.get("/interview", response_model=list[InterviewSessionSummary])
async def get_interviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """List the current user's interview sessions, newest first and
    the dashboard's recent-interviews list and the documents page.
    """
    sessions = await list_interview_sessions(user.id, db)
    data = [InterviewSessionSummary.model_validate(s) for s in sessions]
    return success_response(data=data, status_code=httpx.codes.OK)


@router.get("/interview/presets", response_model=list[InterviewPresetResponse])
async def get_interview_presets(
    coding_assessment_expected: bool | None = None,
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """The interview presets a candidate can pick from. Pass
    coding_assessment_expected=false to leave out presets that need a
    coding round.
    """
    presets = list_interview_presets(coding_expected=coding_assessment_expected)
    data = [InterviewPresetResponse(**p) for p in presets]
    return success_response(data=data, status_code=httpx.codes.OK)


@router.post("/interview/start", response_model=InterviewTurnResponse)
async def start(
    payload: InterviewStartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Create a new interview session for a candidate profile + job
    description pair, and generate the phase 1 opening message.
    """
    try:
        session = await start_interview(
            candidate_profile_id=payload.candidate_profile_id,
            job_description_id=payload.job_description_id,
            user_id=user.id,
            db=db,
            preset_key=payload.preset_key,
            duration_minutes=payload.duration_minutes,
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InvalidInterviewPresetError as exc:
        return error_response(
            message=str(exc), status_code=httpx.codes.UNPROCESSABLE_ENTITY
        )

    return success_response(
        data=build_turn_response(session), status_code=httpx.codes.CREATED
    )


@router.post("/interview/{session_id}/turn", response_model=InterviewTurnResponse)
async def turn(
    session_id: int,
    payload: InterviewTurnRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Submit one candidate turn and get the Interviewer agent's reply."""
    try:
        session = await submit_turn(
            session_id=session_id, message=payload.message, user_id=user.id, db=db
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InterviewSessionNotActiveError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.CONFLICT)

    return success_response(
        data=build_turn_response(session), status_code=httpx.codes.OK
    )


@router.post("/interview/{session_id}/report", response_model=InterviewReportResponse)
async def create_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Run all 5 Judge agents over the finished transcript and persist a
    new evaluation report. Allowed for a "completed" or "ended_early"
    session, not "in_progress".
    """
    try:
        session = await get_interview_session_or_404(session_id, db, user_id=user.id)
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    try:
        report = await generate_report(session=session, db=db)
    except InterviewSessionNotReadyForReportError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.CONFLICT)

    evaluations = await get_report_evaluations(report, db)
    data = InterviewReportResponse.from_report_and_evaluations(
        report, evaluations, session
    )
    return success_response(data=data, status_code=httpx.codes.CREATED)


@router.get("/interview/{session_id}/report", response_model=InterviewReportResponse)
async def read_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Fetch the most recently generated report for a session, without
    re-running the Judges.
    """
    try:
        session = await get_interview_session_or_404(session_id, db, user_id=user.id)
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    try:
        report = await get_latest_report(session=session, db=db)
    except InterviewReportNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    evaluations = await get_report_evaluations(report, db)
    data = InterviewReportResponse.from_report_and_evaluations(
        report, evaluations, session
    )
    return success_response(data=data, status_code=httpx.codes.OK)
