import uuid

import structlog.testing
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.constants.logging import REQUEST_ID_HEADER
from app.core.request_logging import RequestLoggingMiddleware


def test_request_gets_a_generated_uuid_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    # must parse as a real UUID, not just be "present" - a fallback like
    # str(None) would also satisfy an "in response.headers" check.
    uuid.UUID(response.headers[REQUEST_ID_HEADER])


def test_incoming_request_id_is_reused_not_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "my-trace-id"})

    assert response.headers[REQUEST_ID_HEADER] == "my-trace-id"


def test_request_handled_is_logged_with_expected_fields(client: TestClient) -> None:
    # capture_logs() disables the configured processor pipeline for its
    # duration, so contextvars (request_id) merging has to be re-added
    # explicitly - otherwise it can't see anything bound mid-request.
    with structlog.testing.capture_logs(
        processors=[structlog.contextvars.merge_contextvars]
    ) as captured:
        response = client.get("/api/v1/health")

    request_logs = [e for e in captured if e["event"] == "request handled"]
    assert len(request_logs) == 1

    entry = request_logs[0]
    assert entry["method"] == "GET"
    assert entry["path"] == "/api/v1/health"
    assert entry["status_code"] == 200
    assert entry["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert isinstance(entry["duration_ms"], int | float)
    assert entry["duration_ms"] >= 0


async def test_duration_ms_is_computed_from_actual_elapsed_time(
    mocker: MockerFixture,
) -> None:
    # Calls dispatch() directly (bypassing the real ASGI/anyio machinery a
    # full HTTP round-trip goes through) - that machinery also calls
    # time.perf_counter internally, and patching the module-global
    # `time.perf_counter` (import time binds a shared reference) would
    # exhaust a short side_effect list against unrelated calls. Isolating
    # to just our own two calls lets duration_ms have one exact,
    # predictable value - catching it being replaced by a constant (e.g.
    # a mutation like `duration_ms = round(2)`) that a loose ">= 0"
    # check would miss.
    mocker.patch(
        "app.core.request_logging.time.perf_counter", side_effect=[100.0, 100.123456]
    )
    request = mocker.MagicMock()
    request.headers = {}
    request.method = "GET"
    request.url.path = "/api/v1/health"

    response = mocker.MagicMock()
    response.headers = {}
    response.status_code = 200
    call_next = mocker.AsyncMock(return_value=response)

    with structlog.testing.capture_logs(
        processors=[structlog.contextvars.merge_contextvars]
    ) as captured:
        await RequestLoggingMiddleware(app=mocker.MagicMock()).dispatch(
            request, call_next
        )

    entry = next(e for e in captured if e["event"] == "request handled")
    assert entry["duration_ms"] == 123.46
