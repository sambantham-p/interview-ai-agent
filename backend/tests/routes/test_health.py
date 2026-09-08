from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.constants.app import SERVICE_NAME


def test_health_returns_success_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "ok"
    assert body["status_code"] == 200
    assert body["data"] == {"service": SERVICE_NAME, "health": "healthy"}
    assert "error" not in body


def test_health_returns_error_envelope_when_it_fails_to_respond(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch("app.routes.health.success_response", side_effect=RuntimeError("boom"))

    response = client.get("/api/v1/health")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["status"] == "error"
    assert body["status_code"] == 500
    assert body["data"] == {"service": SERVICE_NAME, "health": "unhealthy"}
    assert body["error"] == {"message": "Service unhealthy"}
