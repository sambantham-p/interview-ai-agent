import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.responses import success_response
from app.schemas.jd import JobDescriptionInput, JobDescriptionResponse
from app.services.jd_service import parse_and_persist_job_description

router = APIRouter(tags=["Job Description"])


@router.post("/jd", response_model=JobDescriptionResponse)
async def submit_job_description(
    payload: JobDescriptionInput, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Accept a full JD paste or a short role description, extract it via
    Gemini, persist it, return it.
    """
    jd = await parse_and_persist_job_description(
        full_text=payload.full_text,
        short_description=payload.short_description,
        db=db,
    )

    data = JobDescriptionResponse.model_validate(jd)
    return success_response(data=data, status_code=httpx.codes.OK)
