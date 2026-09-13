from app.core.config import Settings, get_settings


def test_settings_reads_database_url_from_explicit_kwarg() -> None:
    settings = Settings(
        database_url="postgresql://user:pass@host/db",
        gemini_api_key="test-key",
        gemini_resume_parsing_model="gemini-3.8-flash",
        gemini_jd_parsing_model="gemini-3.8-flash",
    )

    assert settings.database_url == "postgresql://user:pass@host/db"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
