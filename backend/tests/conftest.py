import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.constants.logging import REQUEST_ID_HEADER
from app.main import app
from app.models.user import User
from app.routes.auth import get_current_user

TEST_USER_ID = "usr_test_authenticated_user"


def pytest_configure(config: pytest.Config) -> None:
    # Tests never need a *real* database/Gemini connection (anything
    # touching one mocks app.core.config.get_database_settings/
    # get_gemini_settings directly) - these fallbacks just satisfy
    # DatabaseSettings/GeminiSettings' required fields so the suite runs
    # the same way with or without a real backend/.env present (a fresh
    # clone, CI, or mutmut's mirrored `mutants/` tree, which excludes
    # gitignored files like .env).
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    os.environ.setdefault("GEMINI_RESUME_PARSING_MODEL", "gemini-3.8-flash")
    os.environ.setdefault("GEMINI_JD_PARSING_MODEL", "gemini-3.8-flash")
    os.environ.setdefault("GEMINI_INTERVIEWER_MODEL", "gemini-3.8-flash")
    os.environ.setdefault("GEMINI_JUDGE_MODEL", "gemini-3.1-pro-preview")
    os.environ.setdefault("ELEVENLABS_API_KEY", "test-key")
    os.environ.setdefault("ELEVENLABS_VOICE_ID", "test-voice-id")
    os.environ.setdefault("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    os.environ.setdefault("REQUEST_ID_SECRET", "sam-interview-ai-agent")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-at-least-32-bytes-long")
    os.environ.setdefault(
        "GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com"
    )


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, headers={REQUEST_ID_HEADER: "sam-interview-ai-agent"})


@pytest.fixture()
def authed_client() -> Iterator[TestClient]:
    """A client pre-authenticated as TEST_USER_ID, for routes that require
    a real signed-in user (resume/JD/interview) - overrides
    get_current_user for the duration of the test only, so it never
    leaks into test_auth.py's own real-JWT tests of that dependency.
    """

    def _fake_current_user() -> User:
        return User(
            id=TEST_USER_ID,
            email="authed-test-user@example.com",
            name="Authed Test User",
            auth_provider="email",
            is_verified=True,
            token_version=0,
            created_at=datetime.now(UTC),
        )

    app.dependency_overrides[get_current_user] = _fake_current_user
    try:
        yield TestClient(app, headers={REQUEST_ID_HEADER: "sam-interview-ai-agent"})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
