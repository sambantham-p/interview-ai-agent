import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.core.session_lookup import get_interview_session_or_404
from app.dto.interview import (
    InterviewPresetResponse,
    InterviewSessionDetail,
    InterviewSessionSummary,
    InterviewStartRequest,
    InterviewTurnRequest,
    InterviewTurnResponse,
    build_session_detail,
    build_turn_response,
)
from app.dto.judge import InterviewReportResponse, ReportListItem
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
    InvalidInterviewPresetError,
    get_interview_with_job,
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
    list_finished_interviews_with_reports,
)
from app.services.report_pdf import build_report_pdf

router = APIRouter(tags=["Interview"])

PDF_MEDIA_TYPE = "application/pdf"


@router.get("/reports", response_model=list[ReportListItem])
async def get_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """The reports collection: every finished interview of the current
    user, newest first, with its score and verdict once a report exists.
    """
    rows = await list_finished_interviews_with_reports(user_id=user.id, db=db)
    data = [ReportListItem.from_parts(*row) for row in rows]
    return success_response(data=data, status_code=httpx.codes.OK)


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


@router.get("/interview/{session_id}", response_model=InterviewSessionDetail)
async def get_interview(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """One interview session with its transcript and timing - what the
    live interview screen loads to resume, and the report screen to show
    the phase-by-phase review.
    """
    try:
        session, job_description = await get_interview_with_job(
            session_id=session_id, user_id=user.id, db=db
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    return success_response(
        data=build_session_detail(session, job_description),
        status_code=httpx.codes.OK,
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


async def _latest_report_response(
    session: InterviewSession, db: AsyncSession
) -> InterviewReportResponse:
    """The session's most recent report as its API DTO. Raises
    InterviewReportNotFoundError if none has been generated.
    """
    report = await get_latest_report(session=session, db=db)
    evaluations = await get_report_evaluations(report, db)
    return InterviewReportResponse.from_report_and_evaluations(
        report, evaluations, session
    )


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
        data = await _latest_report_response(session, db)
    except InterviewReportNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    return success_response(data=data, status_code=httpx.codes.OK)


@router.post("/interview/{session_id}/report/pdf")
async def download_report_pdf(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Render the session's latest report as a PDF download, without
    re-running the Judges.
    """
    try:
        session, job_description = await get_interview_with_job(
            session_id=session_id, user_id=user.id, db=db
        )
        report = await _latest_report_response(session, db)
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)
    except InterviewReportNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    pdf = build_report_pdf(report, build_session_detail(session, job_description))
    return Response(
        content=pdf,
        media_type=PDF_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="interview-report-{session_id}.pdf"'
        },
    )
