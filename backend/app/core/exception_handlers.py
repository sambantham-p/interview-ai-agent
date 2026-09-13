import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.gemini_client import GeminiResponseParseError, GeminiTransientError
from app.core.responses import error_response
from app.services.jd_service import JobDescriptionExtractionError


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return error_response(message=str(exc.detail), status_code=exc.status_code)


_VALIDATION_ERROR_FIELDS = {"type", "loc", "msg"}


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Pydantic's raw errors() include "input" (the full submitted value,
    # can be large) and "url"/"ctx" (docs link, internal context) - drop
    # those, keep only what a client needs to fix the request.
    errors = [
        {k: v for k, v in error.items() if k in _VALIDATION_ERROR_FIELDS}
        for error in exc.errors()
    ]
    return error_response(
        message="Validation error",
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        data={"errors": jsonable_encoder(errors)},
    )


async def handle_gemini_transient_error(
    request: Request, exc: GeminiTransientError
) -> JSONResponse:
    return error_response(
        message="Gemini processing is temporarily unavailable, try again shortly",
        status_code=httpx.codes.SERVICE_UNAVAILABLE,
    )


async def handle_gemini_response_parse_error(
    request: Request, exc: GeminiResponseParseError
) -> JSONResponse:
    return error_response(
        message="Gemini could not process this submission right now",
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
    )


async def handle_job_description_extraction_error(
    request: Request, exc: JobDescriptionExtractionError
) -> JSONResponse:
    # Deliberate stop, not transient - unusable JD input, don't proceed.
    return error_response(
        message=str(exc),
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        message="Internal server error", status_code=httpx.codes.INTERNAL_SERVER_ERROR
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(GeminiTransientError, handle_gemini_transient_error)
    app.add_exception_handler(
        GeminiResponseParseError, handle_gemini_response_parse_error
    )
    app.add_exception_handler(
        JobDescriptionExtractionError, handle_job_description_extraction_error
    )
    app.add_exception_handler(Exception, handle_unexpected_exception)
