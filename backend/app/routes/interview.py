import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.core.session_lookup import get_interview_session_or_404
from app.models.interview_report import InterviewReport
from app.models.interview_session import InterviewSession
from app.schemas.interview import (
    InterviewStartRequest,
    InterviewTurnRequest,
    InterviewTurnResponse,
)
from app.schemas.judge import InterviewReportResponse, JudgeEvaluationResponse
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
    start_interview,
    submit_turn,
)
from app.services.judge_service import (
    InterviewReportNotFoundError,
    InterviewSessionNotReadyForReportError,
    generate_report,
    get_evaluations_by_ids,
    get_latest_report,
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


async def _report_response(
    report: InterviewReport, session: InterviewSession, db: AsyncSession
) -> InterviewReportResponse:
    evaluations = await get_evaluations_by_ids(report.judge_evaluation_ids, db)
    return InterviewReportResponse(
        id=report.id,
        session_id=report.session_id,
        overall_score=float(report.overall_score),
        recommendation_tier=report.recommendation_tier,
        weights_used=report.weights_used,
        judge_evaluations=[
            JudgeEvaluationResponse.model_validate(e) for e in evaluations
        ],
        hint_counts=session.hint_counts,
        red_flag_count=session.red_flag_count,
        end_reason=session.end_reason,
    )


@router.post("/interview/{session_id}/report", response_model=InterviewReportResponse)
async def create_report(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Run all 5 Judge agents over the finished transcript and persist a
    new evaluation report. Allowed for a "completed" or "ended_early"
    session, not "in_progress".
    """
    try:
        report = await generate_report(session_id=session_id, db=db)
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InterviewSessionNotReadyForReportError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.CONFLICT)

    session = await get_interview_session_or_404(session_id, db)
    return success_response(
        data=await _report_response(report, session, db),
        status_code=httpx.codes.CREATED,
    )


@router.get("/interview/{session_id}/report", response_model=InterviewReportResponse)
async def read_report(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Fetch the most recently generated report for a session, without
    re-running the Judges.
    """
    try:
        report = await get_latest_report(session_id=session_id, db=db)
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InterviewReportNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    session = await get_interview_session_or_404(session_id, db)
    return success_response(
        data=await _report_response(report, session, db),
        status_code=httpx.codes.OK,
    )
