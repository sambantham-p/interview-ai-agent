import httpx
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.resume import PDF_MAGIC_BYTES, PDF_MIME_TYPE
from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.schemas.resume import ResumeUploadResponse
from app.services.resume_service import parse_and_persist_resume

router = APIRouter(tags=["resume"])


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Accept a resume PDF, parse it via Gemini, persist it, return it.

    Gemini/DB failures aren't caught here - GeminiTransientError and
    GeminiResponseParseError (app/core/gemini_client.py) are handled by
    the app-wide handlers registered in app/core/exception_handlers.py;
    anything else falls through to that module's generic 500 handler.
    """
    contents = await file.read()

    if not contents.startswith(PDF_MAGIC_BYTES):
        return error_response(
            message=f"Expected a {PDF_MIME_TYPE} file",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )

    profile = await parse_and_persist_resume(contents, db)

    data = ResumeUploadResponse.model_validate(profile)
    return success_response(data=data, status_code=httpx.codes.OK)
