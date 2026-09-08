from app.core.config import Settings, get_settings


def test_settings_reads_database_url_from_explicit_kwarg() -> None:
    settings = Settings(database_url="postgresql://user:pass@host/db")

    assert settings.database_url == "postgresql://user:pass@host/db"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
