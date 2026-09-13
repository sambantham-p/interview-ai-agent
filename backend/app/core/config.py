from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str
    gemini_resume_parsing_model: str
    gemini_jd_parsing_model: str


class ElevenLabsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    elevenlabs_model_id: str


class SecuritySettings(BaseSettings):
    """The X-Request-ID gate value (see app/core/request_logging.py) -
    kept out of source/constants since it functions as a shared secret,
    not a trace id.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    request_id_secret: str


class GatewaySettings(BaseSettings):
    """Configuration for routing LLM tasks to specific models.
    Defines the model to use for each task or agent role, keeping model
    selection centralized in configuration. Add a field here when a new
    task requires its own model.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_interviewer_model: str

    def model_for_task(self, task: str) -> str:
        routes = {"interviewer": self.gemini_interviewer_model}
        if task not in routes:
            raise KeyError(f"No model route configured for task {task!r}")
        return routes[task]


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache
def get_gemini_settings() -> GeminiSettings:
    return GeminiSettings()


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()


@lru_cache
def get_elevenlabs_settings() -> ElevenLabsSettings:
    return ElevenLabsSettings()


@lru_cache
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()
