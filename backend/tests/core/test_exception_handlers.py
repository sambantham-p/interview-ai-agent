import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exception_handlers import (
    handle_http_exception,
    handle_unexpected_exception,
    handle_validation_error,
    register_exception_handlers,
)


def test_register_exception_handlers_wires_expected_handlers() -> None:
    app = FastAPI()

    register_exception_handlers(app)

    assert app.exception_handlers[StarletteHTTPException] is handle_http_exception
    assert app.exception_handlers[RequestValidationError] is handle_validation_error
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
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["error"] == {"message": "Validation error"}
    assert body["data"]["errors"][0]["msg"] == "field required"


async def test_handle_unexpected_exception_returns_enveloped_500() -> None:
    response = await handle_unexpected_exception(request=None, exc=Exception("boom"))

    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["error"] == {"message": "Internal server error"}
