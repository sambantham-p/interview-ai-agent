import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


def pytest_configure(config: pytest.Config) -> None:
    # Tests never need a *real* database/Gemini connection (anything
    # touching one mocks app.core.config.get_settings directly) - these
    # fallbacks just satisfy Settings' required fields so the suite runs
    # the same way with or without a real backend/.env present (a fresh
    # clone, CI, or mutmut's mirrored `mutants/` tree, which excludes
    # gitignored files like .env).
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    os.environ.setdefault("GEMINI_RESUME_PARSING_MODEL", "gemini-3.8-flash")
    os.environ.setdefault("GEMINI_JD_PARSING_MODEL", "gemini-3.8-flash")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
