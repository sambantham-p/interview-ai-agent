from app.core.config import (
    DatabaseSettings,
    ElevenLabsSettings,
    GeminiSettings,
    get_database_settings,
    get_elevenlabs_settings,
    get_gemini_settings,
)


def test_database_settings_reads_database_url_from_explicit_kwarg() -> None:
    settings = DatabaseSettings(database_url="postgresql://user:pass@host/db")

    assert settings.database_url == "postgresql://user:pass@host/db"


def test_gemini_settings_reads_fields_from_explicit_kwargs() -> None:
    settings = GeminiSettings(
        gemini_api_key="test-key",
        gemini_resume_parsing_model="gemini-3.8-flash",
        gemini_jd_parsing_model="gemini-3.8-flash",
    )

    assert settings.gemini_api_key == "test-key"


def test_get_database_settings_is_cached() -> None:
    assert get_database_settings() is get_database_settings()


def test_get_gemini_settings_is_cached() -> None:
    assert get_gemini_settings() is get_gemini_settings()


def test_elevenlabs_settings_reads_fields_from_explicit_kwargs() -> None:
    settings = ElevenLabsSettings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="voice-1",
        elevenlabs_model_id="eleven_multilingual_v2",
    )

    assert settings.elevenlabs_voice_id == "voice-1"


def test_get_elevenlabs_settings_is_cached() -> None:
    assert get_elevenlabs_settings() is get_elevenlabs_settings()
