from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.models.interview_session import InterviewSession
from app.services.interview_service import (
    InterviewSessionNotActiveError,
    InterviewSessionNotFoundError,
)


def _fake_session(**overrides) -> InterviewSession:
    defaults = {
        "id": 10,
        "candidate_profile_id": 1,
        "job_description_id": 2,
        "current_phase": "background_check",
        "status": "in_progress",
        "transcript": [{"role": "model", "text": "Welcome, let's begin."}],
        "red_flag_count": 0,
        "red_flag_warning_issued": False,
        "hint_counts": {},
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return InterviewSession(**defaults)


def test_start_interview_returns_session_and_opening_reply(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.start_interview",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )

    response = client.post(
        "/api/v1/interview/start",
        json={"candidate_profile_id": 1, "job_description_id": 2},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["reply"] == "Welcome, let's begin."
    assert body["data"]["current_phase"] == "background_check"


def test_start_interview_returns_404_when_profile_or_jd_missing(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.start_interview",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No candidate profile with id 1"),
    )

    response = client.post(
        "/api/v1/interview/start",
        json={"candidate_profile_id": 1, "job_description_id": 2},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_turn_returns_reply_and_updated_phase(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(
            current_phase="project_drill_down",
            transcript=[{"role": "model", "text": "Let's talk about your project."}],
        ),
    )

    response = client.post(
        "/api/v1/interview/10/turn", json={"message": "I studied at XYZ University"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["reply"] == "Let's talk about your project."
    assert body["data"]["current_phase"] == "project_drill_down"


def test_turn_returns_404_when_session_missing(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No interview session with id 99"),
    )

    response = client.post("/api/v1/interview/99/turn", json={"message": "hello"})

    assert response.status_code == 404


def test_turn_returns_409_when_session_not_active(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotActiveError("Interview session 10 is completed"),
    )

    response = client.post("/api/v1/interview/10/turn", json={"message": "hello"})

    assert response.status_code == 409


def test_turn_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/api/v1/interview/10/turn", json={"message": ""})

    assert response.status_code == 422
