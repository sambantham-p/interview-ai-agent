import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import success_response
from app.dto.jd import JobDescriptionInput, JobDescriptionResponse
from app.models.interview_session import InterviewSession
from app.models.job_description import JobDescription
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.document_service import delete_document
from app.services.jd_service import (
    list_job_descriptions,
    parse_and_persist_job_description,
)

router = APIRouter(tags=["Job Description"])


@router.get("/jd", response_model=list[JobDescriptionResponse])
async def get_job_descriptions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """List the current user's submitted job descriptions, newest first."""
    jds = await list_job_descriptions(user.id, db)
    data = [JobDescriptionResponse.model_validate(jd) for jd in jds]
    return success_response(data=data, status_code=httpx.codes.OK)


@router.post("/jd", response_model=JobDescriptionResponse)
async def submit_job_description(
    payload: JobDescriptionInput,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Accept a full JD paste or a short role description, extract it via
    Gemini, persist it, return it.
    """
    jd = await parse_and_persist_job_description(
        full_text=payload.full_text,
        short_description=payload.short_description,
        db=db,
        user_id=user.id,
    )

    data = JobDescriptionResponse.model_validate(jd)
    return success_response(data=data, status_code=httpx.codes.OK)


@router.delete("/jd/{jd_id}")
async def delete_job_description(
    jd_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Permanently delete one of the current user's job descriptions,
    unless an in-progress interview still uses it.
    """
    await delete_document(
        JobDescription,
        InterviewSession.job_description_id,
        document_id=jd_id,
        user_id=user.id,
        db=db,
        label="job description",
    )
    return success_response(data={"id": jd_id}, status_code=httpx.codes.OK)
