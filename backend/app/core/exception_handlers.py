import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.elevenlabs_client import ElevenLabsRequestError, ElevenLabsTransientError
from app.core.gemini_client import GeminiResponseParseError, GeminiTransientError
from app.core.responses import error_response
from app.core.security import InvalidSessionTokenError
from app.services.jd_service import JobDescriptionExtractionError
from app.services.resume_service import ResumeExtractionError


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
    # Gemini returned a response that didn't match the requested schema -
    # a provider-side failure, not an invalid submission, so this isn't a 422.
    return error_response(
        message="Gemini returned an unexpected response, try again shortly",
        status_code=httpx.codes.BAD_GATEWAY,
    )


async def handle_elevenlabs_transient_error(
    request: Request, exc: ElevenLabsTransientError
) -> JSONResponse:
    return error_response(
        message="Voice synthesis is temporarily unavailable, try again shortly",
        status_code=httpx.codes.SERVICE_UNAVAILABLE,
    )


async def handle_elevenlabs_request_error(
    request: Request, exc: ElevenLabsRequestError
) -> JSONResponse:
    # Deliberate stop, not transient - ElevenLabs rejected this specific
    # request (bad voice_id, a plan-restricted voice, invalid text). Use
    # its own status_code/message instead of a generic 500.
    return error_response(message=str(exc), status_code=exc.status_code)


async def handle_job_description_extraction_error(
    request: Request, exc: JobDescriptionExtractionError
) -> JSONResponse:
    # Deliberate stop, not transient - unusable JD input, don't proceed.
    return error_response(
        message=str(exc),
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
    )


async def handle_resume_extraction_error(
    request: Request, exc: ResumeExtractionError
) -> JSONResponse:
    # Deliberate stop, not transient - nothing usable extracted, don't
    # persist an empty profile.
    return error_response(
        message=str(exc),
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
    )


async def handle_invalid_session_token_error(
    request: Request, exc: InvalidSessionTokenError
) -> JSONResponse:
    # Raised from inside a FastAPI dependency (get_current_user)
    return error_response(message=str(exc), status_code=httpx.codes.UNAUTHORIZED)


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
        ElevenLabsTransientError, handle_elevenlabs_transient_error
    )
    app.add_exception_handler(ElevenLabsRequestError, handle_elevenlabs_request_error)
    app.add_exception_handler(
        JobDescriptionExtractionError, handle_job_description_extraction_error
    )
    app.add_exception_handler(ResumeExtractionError, handle_resume_extraction_error)
    app.add_exception_handler(
        InvalidSessionTokenError, handle_invalid_session_token_error
    )
    app.add_exception_handler(Exception, handle_unexpected_exception)
