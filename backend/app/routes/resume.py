import httpx
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.resume import (
    MAX_RESUME_SIZE_BYTES,
    PDF_EOF_MARKER,
    PDF_MAGIC_BYTES,
    PDF_MIME_TYPE,
)
from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.dto.resume import ResumeUploadResponse
from app.models.candidate_profile import CandidateProfile
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.document_service import delete_document
from app.services.resume_service import list_resumes, parse_and_persist_resume

router = APIRouter(tags=["resume"])


@router.get("/resume", response_model=list[ResumeUploadResponse])
async def get_resumes(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """List the current user's uploaded resumes, newest first."""
    profiles = await list_resumes(user.id, db)
    data = [ResumeUploadResponse.model_validate(p) for p in profiles]
    return success_response(data=data, status_code=httpx.codes.OK)


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Accept a resume PDF, parse it via Gemini, persist it, return it.

    Gemini/DB failures aren't caught here - GeminiTransientError and
    GeminiResponseParseError (app/core/gemini_client.py) are handled by
    the app-wide handlers registered in app/core/exception_handlers.py;
    anything else falls through to that module's generic 500 handler.
    """
    contents = await file.read(MAX_RESUME_SIZE_BYTES + 1)

    if len(contents) > MAX_RESUME_SIZE_BYTES:
        return error_response(
            message=(
                "This file is larger than 10 MB. Please upload a smaller "
                "PDF of your resume."
            ),
            status_code=httpx.codes.REQUEST_ENTITY_TOO_LARGE,
        )

    if (
        not contents.startswith(PDF_MAGIC_BYTES)
        or PDF_EOF_MARKER not in contents[-1024:]
    ):
        return error_response(
            message=(
                "This doesn't look like a valid PDF file. Please upload your "
                f"resume as a PDF ({PDF_MIME_TYPE})."
            ),
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )

    profile = await parse_and_persist_resume(contents, db, user_id=user.id)

    data = ResumeUploadResponse.model_validate(profile)
    return success_response(data=data, status_code=httpx.codes.OK)


@router.delete("/resume/{resume_id}")
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Permanently delete one of the current user's resumes, unless a
    in-progress interview still uses it.
    """
    await delete_document(
        CandidateProfile,
        InterviewSession.candidate_profile_id,
        document_id=resume_id,
        user_id=user.id,
        db=db,
        label="resume",
    )
    return success_response(data={"id": resume_id}, status_code=httpx.codes.OK)
