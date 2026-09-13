from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.constants.responses import RESPONSE_STATUS_ERROR, RESPONSE_STATUS_OK
from app.schemas.response import APIResponse, ErrorDetail


def success_response(
    data: Any = None, status_code: int = httpx.codes.OK
) -> JSONResponse:
    envelope = APIResponse(
        success=True,
        status=RESPONSE_STATUS_OK,
        status_code=status_code,
        data=data,
    )
    return JSONResponse(
        status_code=status_code, content=jsonable_encoder(envelope, exclude={"error"})
    )


def error_response(message: str, status_code: int, data: Any = None) -> JSONResponse:
    envelope = APIResponse(
        success=False,
        status=RESPONSE_STATUS_ERROR,
        status_code=status_code,
        data=data,
        error=ErrorDetail(message=message),
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))
