import time
import uuid

import httpx
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.constants.logging import (
    REQUEST_ID_HEADER,
    REQUEST_ID_OPTIONAL_PATHS,
    TRACE_ID_HEADER,
)
from app.core.config import get_security_settings
from app.core.responses import error_response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Gates every route behind a fixed X-Request-ID value (except
    REQUEST_ID_OPTIONAL_PATHS, which infra health-checkers and a browser
    loading Swagger/ReDoc can't be expected to send it on), and separately
    binds a real unique-per-request trace id to every log line emitted
    while handling that request (so unrelated concurrent requests never
    mix in the logs). Logs exactly one line per request: method, path,
    status, duration.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER)
        expected_request_id = get_security_settings().request_id_secret

        if request_id != expected_request_id and request.url.path not in (
            REQUEST_ID_OPTIONAL_PATHS
        ):
            logger.warning("request_id_invalid", path=request.url.path)
            return error_response(
                message=f"{REQUEST_ID_HEADER} header is missing or invalid",
                status_code=httpx.codes.UNAUTHORIZED,
            )

        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=trace_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers[TRACE_ID_HEADER] = trace_id
        logger.info(
            "request handled",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
