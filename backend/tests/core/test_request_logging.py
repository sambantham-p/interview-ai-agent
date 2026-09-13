import uuid

import pytest
import structlog.testing
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.constants.logging import REQUEST_ID_HEADER, TRACE_ID_HEADER
from app.core.config import get_security_settings
from app.core.request_logging import RequestLoggingMiddleware
from app.main import app


def test_correct_request_id_is_allowed_and_gets_a_unique_trace_id(
    client: TestClient,
) -> None:
    # `client` fixture already sends the expected X-Request-ID (see
    # tests/conftest.py) - this confirms it's let through and gets back a
    # real, unique trace id on a separate header.
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    uuid.UUID(response.headers[TRACE_ID_HEADER])


def test_two_requests_get_different_trace_ids(client: TestClient) -> None:
    first = client.get("/api/v1/health")
    second = client.get("/api/v1/health")

    assert first.headers[TRACE_ID_HEADER] != second.headers[TRACE_ID_HEADER]


def test_missing_request_id_is_rejected_on_a_real_endpoint() -> None:
    bare_client = TestClient(app)

    response = bare_client.post("/api/v1/voice/tts", json={"text": "hi"})

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert REQUEST_ID_HEADER in body["error"]["message"]


def test_wrong_request_id_value_is_rejected_on_a_real_endpoint() -> None:
    bare_client = TestClient(app, headers={REQUEST_ID_HEADER: "not-the-right-value"})

    response = bare_client.post("/api/v1/voice/tts", json={"text": "hi"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "path", ["/api/v1/health", "/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json"]
)
def test_missing_request_id_is_allowed_on_optional_paths(path: str) -> None:
    bare_client = TestClient(app)

    response = bare_client.get(path)

    assert response.status_code != 401
    uuid.UUID(response.headers[TRACE_ID_HEADER])


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
    assert entry["request_id"] == response.headers[TRACE_ID_HEADER]
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
    request.headers = {REQUEST_ID_HEADER: get_security_settings().request_id_secret}
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
