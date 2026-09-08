import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


def pytest_configure(config: pytest.Config) -> None:
    # Tests never need a *real* database connection (anything touching one
    # mocks app.core.config.get_settings directly) - this fallback just
    # satisfies Settings' required database_url field so the suite runs
    # the same way with or without a real backend/.env present (a fresh
    # clone, CI, or mutmut's mirrored `mutants/` tree, which excludes
    # gitignored files like .env).
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
