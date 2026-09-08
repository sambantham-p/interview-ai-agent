import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return error_response(message=str(exc.detail), status_code=exc.status_code)


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(
        message="Validation error",
        status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        data={"errors": jsonable_encoder(exc.errors())},
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        message="Internal server error", status_code=httpx.codes.INTERNAL_SERVER_ERROR
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
