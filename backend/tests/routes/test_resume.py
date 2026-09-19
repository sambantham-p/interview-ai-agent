from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.gemini_client import GeminiResponseParseError, GeminiTransientError
from app.main import app
from app.models.candidate_profile import CandidateProfile
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.resume_service import ResumeExtractionError
from tests.conftest import TEST_USER_ID


def _fake_upload_file() -> tuple[str, tuple[str, bytes, str]]:
    return "file", ("resume.pdf", b"%PDF-1.4 fake pdf bytes %%EOF", "application/pdf")


def test_upload_resume_rejects_content_without_a_pdf_signature(
    authed_client: TestClient,
) -> None:
    response = authed_client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "application/pdf" in body["error"]["message"]


def test_upload_resume_rejects_non_pdf_bytes_even_if_labeled_as_pdf(
    authed_client: TestClient,
) -> None:
    # The Content-Type header is client-supplied and untrustworthy alone -
    # only the file's own magic bytes decide what it actually is.
    response = authed_client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_upload_resume_rejects_a_pdf_signature_with_no_eof_trailer(
    authed_client: TestClient,
) -> None:
    # A truncated/malformed file can still start with the PDF magic bytes -
    # the trailing %%EOF marker catches what the header check alone misses.
    response = authed_client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 no trailer here", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_upload_resume_rejects_a_file_over_the_size_limit(
    authed_client: TestClient,
) -> None:
    from app.constants.resume import MAX_RESUME_SIZE_BYTES

    oversized = b"%PDF-1.4 " + b"a" * MAX_RESUME_SIZE_BYTES + b" %%EOF"

    response = authed_client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.pdf", oversized, "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["success"] is False


def test_upload_resume_accepts_a_real_pdf_with_a_generic_content_type(
    authed_client: TestClient, mocker: MockerFixture
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

    response = authed_client.post(
        "/api/v1/resume/upload",
        files={
            "file": (
                "resume.pdf",
                b"%PDF-1.4 fake pdf bytes %%EOF",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 200


def test_upload_resume_returns_persisted_profile_on_success(
    authed_client: TestClient, mocker: MockerFixture
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

    response = authed_client.post(
        "/api/v1/resume/upload", files=dict([_fake_upload_file()])
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == 1
    assert body["data"]["skills"] == ["Python"]
    assert body["data"]["github_url"] == "https://github.com/example"


def test_upload_resume_returns_503_for_a_transient_gemini_failure(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    # GeminiTransientError (network error, 5xx, 429 - see
    # gemini_client.py) is handled app-wide by
    # app/core/exception_handlers.py, not by this route.
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=GeminiTransientError("gemini down"),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post(
        "/api/v1/resume/upload", files=dict([_fake_upload_file()])
    )

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_upload_resume_returns_502_when_gemini_response_does_not_parse(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=GeminiResponseParseError("nothing extractable"),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post(
        "/api/v1/resume/upload", files=dict([_fake_upload_file()])
    )

    assert response.status_code == 502
    assert response.json()["success"] is False


def test_upload_resume_returns_422_when_nothing_usable_was_extracted(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    # A blank/image-only PDF that still passes the magic-bytes check but
    # extracts nothing usable must not silently persist an empty profile.
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=ResumeExtractionError(
            "Could not extract any education, experience, projects, or "
            "skills from this resume"
        ),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post(
        "/api/v1/resume/upload", files=dict([_fake_upload_file()])
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "Could not extract" in body["error"]["message"]


def test_upload_resume_returns_500_for_an_unexpected_failure(
    mocker: MockerFixture,
) -> None:
    # Anything not GeminiTransientError/GeminiResponseParseError (a DB
    # error, a bug) falls through to the generic 500 handler - the route
    # itself has no try/except of its own. Needs raise_server_exceptions
    # =False: Starlette's ServerErrorMiddleware is what handles a bare
    # Exception, and TestClient re-raises in-process instead of returning
    # its response unless told not to.
    mocker.patch(
        "app.routes.resume.parse_and_persist_resume",
        side_effect=RuntimeError("db exploded"),
        new_callable=mocker.AsyncMock,
    )
    app.dependency_overrides[get_current_user] = lambda: User(
        id=TEST_USER_ID,
        email="authed-test-user@example.com",
        name="Authed Test User",
        auth_provider="email",
        is_verified=True,
        token_version=0,
        created_at=datetime.now(UTC),
    )
    try:
        authed_client = TestClient(
            app,
            raise_server_exceptions=False,
            headers={"X-Request-ID": "sam-interview-ai-agent"},
        )

        response = authed_client.post(
            "/api/v1/resume/upload", files=dict([_fake_upload_file()])
        )

        assert response.status_code == 500
        assert response.json()["success"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_get_resumes_returns_the_users_resumes(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.resume.list_resumes",
        new_callable=mocker.AsyncMock,
        return_value=[
            CandidateProfile(
                id=1,
                education=[],
                experience=[],
                projects=[],
                skills=["Python"],
                github_url=None,
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ],
    )

    response = authed_client.get("/api/v1/resume")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"][0]["skills"] == ["Python"]


def test_get_resumes_returns_empty_list_when_user_has_none(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.resume.list_resumes",
        new_callable=mocker.AsyncMock,
        return_value=[],
    )

    response = authed_client.get("/api/v1/resume")

    assert response.status_code == 200
    assert response.json()["data"] == []
