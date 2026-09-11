from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.models.candidate_profile import CandidateProfile


def _fake_upload_file() -> tuple[str, tuple[str, bytes, str]]:
    return "file", ("resume.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")


def test_upload_resume_rejects_content_without_a_pdf_signature(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "application/pdf" in body["error"]["message"]


def test_upload_resume_rejects_non_pdf_bytes_even_if_labeled_as_pdf(
    client: TestClient,
) -> None:
    # The Content-Type header is client-supplied and untrustworthy alone -
    # only the file's own magic bytes decide what it actually is.
    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_upload_resume_accepts_a_real_pdf_with_a_generic_content_type(
    client: TestClient, mocker: MockerFixture
) -> None:
    # A real PDF sent with a missing/generic Content-Type (common from
    # non-browser clients) must not be wrongly rejected.
    fake_profile = CandidateProfile(
        id=1,
        education=[],
        experience=[],
        projects=[],
        skills=[],
        github_url=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        return_value=fake_profile,
        new_callable=mocker.AsyncMock,
    )

    response = client.post(
        "/api/v1/resume/upload",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4 fake pdf bytes",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 200


def test_upload_resume_returns_persisted_profile_on_success(
    client: TestClient, mocker: MockerFixture
) -> None:
    fake_profile = CandidateProfile(
        id=1,
        education=[],
        experience=[],
        projects=[],
        skills=["Python"],
        github_url="https://github.com/example",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        return_value=fake_profile,
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/resume/upload", files=dict([_fake_upload_file()]))

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == 1
    assert body["data"]["skills"] == ["Python"]
    assert body["data"]["github_url"] == "https://github.com/example"


def test_upload_resume_returns_503_when_a_raw_httpx_error_is_raised(
    client: TestClient, mocker: MockerFixture
) -> None:
    error = httpx.ConnectError("boom")
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=error,
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/resume/upload", files=dict([_fake_upload_file()]))

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_upload_resume_returns_503_for_gemini_sdk_connection_errors(
    client: TestClient, mocker: MockerFixture
) -> None:
    # google-genai's real Interactions-API connection/timeout errors
    # (APIConnectionError/APITimeoutError) live in a private _gaos
    # submodule, unsafe to import directly (see app/routes/resume.py's
    # comment) - this simulates one by class name only, the same way the
    # route itself detects it, without importing the private type.
    class APIConnectionError(Exception):
        pass

    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=APIConnectionError("gemini unreachable"),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/resume/upload", files=dict([_fake_upload_file()]))

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_upload_resume_returns_422_when_extraction_fails_for_any_other_reason(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=ValueError("nothing extractable"),
        new_callable=mocker.AsyncMock,
    )

    response = client.post("/api/v1/resume/upload", files=dict([_fake_upload_file()]))

    assert response.status_code == 422
    assert response.json()["success"] is False
