from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.gemini_client import GeminiResponseParseError, GeminiTransientError
from app.main import app
from app.models.job_description import JobDescription
from app.services.jd_service import JobDescriptionExtractionError


def _fake_job_description() -> JobDescription:
    return JobDescription(
        id=1,
        role="Backend Engineer",
        seniority="senior",
        tech_stack=["Python", "FastAPI"],
        coding_assessment_expected=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_submit_jd_rejects_neither_input_mode(client: TestClient) -> None:
    response = client.post("/api/v1/jd", json={})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_submit_jd_rejects_both_input_modes(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jd",
        json={"full_text": "full JD text", "short_description": "short version"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_submit_jd_returns_persisted_jd_on_success_with_full_text(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        return_value=_fake_job_description(),
        new_callable=mocker.AsyncMock,
    )

    response = client.post(
        "/api/v1/jd",
        json={"full_text": "We are hiring a Senior Backend Engineer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["role"] == "Backend Engineer"
    assert body["data"]["tech_stack"] == ["Python", "FastAPI"]


def test_submit_jd_returns_persisted_jd_on_success_with_short_description(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        return_value=_fake_job_description(),
        new_callable=mocker.AsyncMock,
    )

    response = client.post(
        "/api/v1/jd", json={"short_description": "AI Engineer, mid-level"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["role"] == "Backend Engineer"


def test_submit_jd_returns_422_when_input_is_not_extractable(
    client: TestClient, mocker: MockerFixture
) -> None:
    # Unextractable JD input must stop the candidate, not start an interview.
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        side_effect=JobDescriptionExtractionError(
            "the text doesn't describe any job role"
        ),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/jd", json={"full_text": "asdkjaslkdj"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["message"] == "the text doesn't describe any job role"


def test_submit_jd_returns_422_for_a_bare_title_submitted_as_full_text(
    client: TestClient, mocker: MockerFixture
) -> None:
    # Real service, only Gemini itself mocked - confirms the word-count
    # guard in app/services/jd_service.py runs on the actual request path,
    # not just when the service is mocked out entirely.
    fake_extract_structured = mocker.patch(
        "app.services.jd_service.extract_structured", new_callable=mocker.AsyncMock
    )

    response = client.post(
        "/api/v1/jd", json={"full_text": "Senior Software Engineer."}
    )

    assert response.status_code == 422
    assert "bare title" in response.json()["error"]["message"]
    fake_extract_structured.assert_not_awaited()


def test_submit_jd_returns_422_for_a_too_short_short_description(
    client: TestClient, mocker: MockerFixture
) -> None:
    fake_extract_structured = mocker.patch(
        "app.services.jd_service.extract_structured", new_callable=mocker.AsyncMock
    )

    response = client.post("/api/v1/jd", json={"short_description": "Engineer"})

    assert response.status_code == 422
    assert "too short" in response.json()["error"]["message"]
    fake_extract_structured.assert_not_awaited()


def test_submit_jd_returns_422_when_required_fields_are_missing(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        side_effect=JobDescriptionExtractionError(
            "Could not determine: tech_stack - add more detail to the job description"
        ),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/jd", json={"full_text": "a real JD"})

    assert response.status_code == 422
    assert "Could not determine" in response.json()["error"]["message"]


def test_submit_jd_returns_503_for_a_transient_gemini_failure(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        side_effect=GeminiTransientError("gemini down"),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/jd", json={"full_text": "a real JD"})

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_submit_jd_returns_422_when_gemini_response_does_not_parse(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        side_effect=GeminiResponseParseError("nothing extractable"),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/jd", json={"full_text": "a real JD"})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_submit_jd_returns_500_for_an_unexpected_failure(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.routes.jd.parse_and_persist_job_description",
        side_effect=RuntimeError("db exploded"),
        new_callable=mocker.AsyncMock,
    )
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/jd", json={"full_text": "a real JD"})

    assert response.status_code == 500
    assert response.json()["success"] is False
