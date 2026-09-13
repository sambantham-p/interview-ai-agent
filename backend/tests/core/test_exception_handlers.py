import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exception_handlers import (
    handle_gemini_response_parse_error,
    handle_gemini_transient_error,
    handle_http_exception,
    handle_job_description_extraction_error,
    handle_unexpected_exception,
    handle_validation_error,
    register_exception_handlers,
)
from app.core.gemini_client import GeminiResponseParseError, GeminiTransientError
from app.services.jd_service import JobDescriptionExtractionError


def test_register_exception_handlers_wires_expected_handlers() -> None:
    app = FastAPI()

    register_exception_handlers(app)

    assert app.exception_handlers[StarletteHTTPException] is handle_http_exception
    assert app.exception_handlers[RequestValidationError] is handle_validation_error
    assert app.exception_handlers[GeminiTransientError] is handle_gemini_transient_error
    assert (
        app.exception_handlers[GeminiResponseParseError]
        is handle_gemini_response_parse_error
    )
    assert (
        app.exception_handlers[JobDescriptionExtractionError]
        is handle_job_description_extraction_error
    )
    assert app.exception_handlers[Exception] is handle_unexpected_exception


def test_unmatched_route_returns_enveloped_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["status_code"] == 404
    assert body["error"] == {"message": "Not Found"}


async def test_handle_validation_error_returns_enveloped_422() -> None:
    exc = RequestValidationError(
        errors=[{"loc": ("body", "email"), "msg": "field required", "type": "missing"}]
    )

    response = await handle_validation_error(request=None, exc=exc)

    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["data"]["errors"][0] == {
        "loc": ["body", "email"],
        "msg": "field required",
        "type": "missing",
    }


async def test_handle_validation_error_strips_the_echoed_input_value() -> None:
    # errors() includes "input" (the full submitted value, can be large)
    # and "url" (a docs link) - these must not be echoed back to clients.
    exc = RequestValidationError(
        errors=[
            {
                "loc": ("body", "full_text"),
                "msg": "Value error, some big payload",
                "type": "value_error",
                "input": "x" * 5000,
                "url": "https://errors.pydantic.dev/2/v/value_error",
                "ctx": {"error": {}},
            }
        ]
    )

    response = await handle_validation_error(request=None, exc=exc)

    body = json.loads(response.body)
    assert set(body["data"]["errors"][0].keys()) == {"loc", "msg", "type"}


async def test_handle_validation_error_returns_enveloped_422_body() -> None:
    exc = RequestValidationError(
        errors=[{"loc": ("body", "email"), "msg": "field required", "type": "missing"}]
    )

    response = await handle_validation_error(request=None, exc=exc)

    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["error"] == {"message": "Validation error"}
    assert body["data"]["errors"][0]["msg"] == "field required"


async def test_handle_gemini_transient_error_returns_enveloped_503() -> None:
    response = await handle_gemini_transient_error(
        request=None, exc=GeminiTransientError("gemini down")
    )

    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["success"] is False
    assert "temporarily unavailable" in body["error"]["message"]


async def test_handle_gemini_response_parse_error_returns_enveloped_422() -> None:
    response = await handle_gemini_response_parse_error(
        request=None, exc=GeminiResponseParseError("did not parse")
    )

    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["success"] is False
    assert "could not process this submission" in body["error"]["message"].lower()


async def test_handle_job_description_extraction_error_returns_enveloped_422() -> None:
    response = await handle_job_description_extraction_error(
        request=None,
        exc=JobDescriptionExtractionError("the text doesn't describe a job role"),
    )

    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"]["message"] == "the text doesn't describe a job role"


async def test_handle_unexpected_exception_returns_enveloped_500() -> None:
    response = await handle_unexpected_exception(request=None, exc=Exception("boom"))

    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["error"] == {"message": "Internal server error"}
