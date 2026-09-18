from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.session_lookup import InterviewSessionNotFoundError
from app.models.interview_report import InterviewReport
from app.models.interview_session import InterviewSession
from app.models.judge_evaluation import JudgeEvaluation
from app.services.interview_service import InterviewSessionNotActiveError
from app.services.judge_service import (
    InterviewReportNotFoundError,
    InterviewSessionNotReadyForReportError,
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
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.start_interview",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )

    response = authed_client.post(
        "/api/v1/interview/start",
        json={"candidate_profile_id": 1, "job_description_id": 2},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["reply"] == "Welcome, let's begin."
    assert body["data"]["current_phase"] == "background_check"


def test_start_interview_returns_404_when_profile_or_jd_missing(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.start_interview",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No candidate profile with id 1"),
    )

    response = authed_client.post(
        "/api/v1/interview/start",
        json={"candidate_profile_id": 1, "job_description_id": 2},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False


def test_turn_returns_reply_and_updated_phase(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(
            current_phase="project_drill_down",
            transcript=[{"role": "model", "text": "Let's talk about your project."}],
        ),
    )

    response = authed_client.post(
        "/api/v1/interview/10/turn", json={"message": "I studied at XYZ University"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["reply"] == "Let's talk about your project."
    assert body["data"]["current_phase"] == "project_drill_down"


def test_turn_returns_404_when_session_missing(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No interview session with id 99"),
    )

    response = authed_client.post(
        "/api/v1/interview/99/turn", json={"message": "hello"}
    )

    assert response.status_code == 404


def test_turn_returns_409_when_session_not_active(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.submit_turn",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotActiveError("Interview session 10 is completed"),
    )

    response = authed_client.post(
        "/api/v1/interview/10/turn", json={"message": "hello"}
    )

    assert response.status_code == 409


def test_turn_rejects_empty_message(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/interview/10/turn", json={"message": ""})

    assert response.status_code == 422


def _fake_judge_evaluation(**overrides) -> JudgeEvaluation:
    defaults = {
        "id": 1,
        "session_id": 10,
        "judge_name": "project_depth",
        "dimension": "Project Depth",
        "score": 80.0,
        "summary": "Solid understanding.",
        "evidence": [{"quote": "q", "transcript_index": 1, "reasoning": "r"}],
    }
    defaults.update(overrides)
    return JudgeEvaluation(**defaults)


def _fake_report(**overrides) -> InterviewReport:
    defaults = {
        "id": 1,
        "session_id": 10,
        "overall_score": 77.5,
        "recommendation_tier": "hire",
        "weights_used": {"project_depth": 0.25},
        "judge_evaluation_ids": [1],
    }
    defaults.update(overrides)
    return InterviewReport(**defaults)


def test_create_report_returns_201_with_full_report(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.generate_report",
        new_callable=mocker.AsyncMock,
        return_value=_fake_report(),
    )
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )
    mocker.patch(
        "app.routes.interview.get_evaluations_by_ids",
        new_callable=mocker.AsyncMock,
        return_value=[_fake_judge_evaluation()],
    )

    response = authed_client.post("/api/v1/interview/10/report")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["overall_score"] == 77.5
    assert body["data"]["recommendation_tier"] == "hire"
    assert body["data"]["judge_evaluations"][0]["judge_name"] == "project_depth"


def test_create_report_returns_404_for_unknown_session(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No interview session with id 99"),
    )

    response = authed_client.post("/api/v1/interview/99/report")

    assert response.status_code == 404


def test_create_report_returns_409_when_session_in_progress(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )
    mocker.patch(
        "app.routes.interview.generate_report",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotReadyForReportError(
            "Interview session 10 is in_progress, not ready for a report"
        ),
    )

    response = authed_client.post("/api/v1/interview/10/report")

    assert response.status_code == 409


def test_read_report_returns_200_with_persisted_report(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.get_latest_report",
        new_callable=mocker.AsyncMock,
        return_value=_fake_report(),
    )
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )
    mocker.patch(
        "app.routes.interview.get_evaluations_by_ids",
        new_callable=mocker.AsyncMock,
        return_value=[_fake_judge_evaluation()],
    )

    response = authed_client.get("/api/v1/interview/10/report")

    assert response.status_code == 200
    assert response.json()["data"]["overall_score"] == 77.5


def test_read_report_returns_404_for_unknown_session(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewSessionNotFoundError("No interview session with id 99"),
    )

    response = authed_client.get("/api/v1/interview/99/report")

    assert response.status_code == 404


def test_read_report_returns_404_when_no_report_generated_yet(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.interview.get_interview_session_or_404",
        new_callable=mocker.AsyncMock,
        return_value=_fake_session(),
    )
    mocker.patch(
        "app.routes.interview.get_latest_report",
        new_callable=mocker.AsyncMock,
        side_effect=InterviewReportNotFoundError(
            "No report generated yet for interview session 10"
        ),
    )

    response = authed_client.get("/api/v1/interview/10/report")

    assert response.status_code == 404
