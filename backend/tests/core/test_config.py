import pytest

from app.constants.judge import LLM_TASK_JUDGE_CODING, LLM_TASK_JUDGE_PROJECT_DEPTH
from app.core.config import (
    CorsSettings,
    DatabaseSettings,
    ElevenLabsSettings,
    GatewaySettings,
    GeminiSettings,
    get_cors_settings,
    get_database_settings,
    get_elevenlabs_settings,
    get_gateway_settings,
    get_gemini_settings,
    get_smtp_settings,
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


def test_gateway_settings_routes_interviewer_task() -> None:
    settings = GatewaySettings(
        gemini_interviewer_model="gemini-3.8-flash",
        gemini_judge_model="gemini-3.1-pro",
        gemini_stt_model="gemini-stt",
        gemini_tts_model="gemini-tts",
        gemini_embedding_model="gemini-embedding",
    )

    assert settings.model_for_task("interviewer") == "gemini-3.8-flash"


def test_gateway_settings_routes_all_judge_tasks_to_judge_model() -> None:
    settings = GatewaySettings(
        gemini_interviewer_model="gemini-3.8-flash",
        gemini_judge_model="gemini-3.1-pro",
        gemini_stt_model="gemini-stt",
        gemini_tts_model="gemini-tts",
        gemini_embedding_model="gemini-embedding",
    )

    assert settings.model_for_task(LLM_TASK_JUDGE_PROJECT_DEPTH) == "gemini-3.1-pro"
    assert settings.model_for_task(LLM_TASK_JUDGE_CODING) == "gemini-3.1-pro"


def test_gateway_settings_raises_key_error_for_unknown_task() -> None:
    settings = GatewaySettings(
        gemini_interviewer_model="gemini-3.8-flash",
        gemini_judge_model="gemini-3.1-pro",
        gemini_stt_model="gemini-stt",
        gemini_tts_model="gemini-tts",
        gemini_embedding_model="gemini-embedding",
    )

    with pytest.raises(KeyError):
        settings.model_for_task("unknown_task")


def test_get_gateway_settings_is_cached() -> None:
    assert get_gateway_settings() is get_gateway_settings()


def test_get_smtp_settings_is_cached() -> None:
    assert get_smtp_settings() is get_smtp_settings()


def test_cors_settings_splits_comma_separated_origins() -> None:
    settings = CorsSettings(
        cors_allowed_origins=" https://a.vercel.app/ , ,http://localhost:5173"
    )

    assert settings.allowed_origins == ["https://a.vercel.app", "http://localhost:5173"]


def test_cors_settings_defaults_to_local_dev_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = CorsSettings(_env_file=None)

    assert settings.allowed_origins == [
        "http://localhost:5173",
        "http://localhost:8080",
    ]


def test_get_cors_settings_is_cached() -> None:
    assert get_cors_settings() is get_cors_settings()
