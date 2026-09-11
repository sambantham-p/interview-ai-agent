import httpx
import structlog
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.resume import PDF_MAGIC_BYTES, PDF_MIME_TYPE
from app.core.db import get_db
from app.core.responses import error_response, success_response
from app.schemas.resume import ResumeUploadResponse
from app.services.resume_service import parse_and_persist_resume

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["resume"])


_GEMINI_TRANSIENT_ERROR_NAMES = {"APIConnectionError", "APITimeoutError"}


def _is_transient_gemini_failure(exc: Exception) -> bool:
    return (
        isinstance(exc, httpx.HTTPError)
        or type(exc).__name__ in _GEMINI_TRANSIENT_ERROR_NAMES
    )


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Accept a resume PDF, parse it via Gemini, persist it, return it."""
    contents = await file.read()

    if not contents.startswith(PDF_MAGIC_BYTES):
        return error_response(
            message=f"Expected a {PDF_MIME_TYPE} file",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )

    try:
        profile = await parse_and_persist_resume(contents, db)
    except Exception as exc:
        if _is_transient_gemini_failure(exc):
            logger.exception("resume parsing: network failure calling Gemini")
            return error_response(
                message="Resume parsing is temporarily unavailable, try again shortly",
                status_code=httpx.codes.SERVICE_UNAVAILABLE,
            )
        logger.exception("resume parsing: extraction or persistence failed")
        return error_response(
            message="Could not process this resume right now",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )

    data = ResumeUploadResponse.model_validate(profile)
    return success_response(data=data, status_code=httpx.codes.OK)
