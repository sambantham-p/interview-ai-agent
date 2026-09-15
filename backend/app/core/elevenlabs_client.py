import time
from functools import lru_cache

import httpx
import structlog
from elevenlabs import AsyncElevenLabs
from elevenlabs.core.api_error import ApiError

from app.constants.voice import (
    ELEVENLABS_CLIENT_TIMEOUT_SECONDS,
    ELEVENLABS_RATE_LIMIT_STATUS_CODE,
    TTS_OUTPUT_FORMAT,
)
from app.core.config import get_elevenlabs_settings

logger = structlog.get_logger(__name__)


class ElevenLabsTransientError(Exception):
    """A retryable ElevenLabs-side failure (network error, 5xx, 429 rate
    limit) - not the caller's fault. Mirrors GeminiTransientError's role
    in gemini_client.py: callers don't inspect the SDK error directly,
    app/core/exception_handlers.py maps this straight to a 503.
    """


class ElevenLabsRequestError(Exception):
    """A non-retryable ElevenLabs rejection of this specific request -
    a bad voice_id, a voice the account's plan can't use (e.g. a
    "professional" Voice Library voice, which stays paid-tier-only even
    after being added to "My Voices" - only "premade" voices are
    free-tier API accessible), invalid text, etc. Carries the real
    status_code and message ElevenLabs returned, so
    app/core/exception_handlers.py can surface *that* to the caller
    instead of collapsing every non-transient failure into one generic
    500 - the same problem CLAUDE.md documents fixing once already for
    Gemini's error types.
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _api_error_message(exc: ApiError) -> str:
    """ElevenLabs' error body is {"detail": {"message": "...", ...}} for
    every documented error - fall back to the raw body if some other
    shape ever comes back, rather than raising while building an error.
    """
    if isinstance(exc.body, dict):
        detail = exc.body.get("detail")
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            return detail["message"]
    return str(exc)


@lru_cache
def get_elevenlabs_client() -> AsyncElevenLabs:
    """Cached ElevenLabs client, built lazily like get_gemini_client()."""
    return AsyncElevenLabs(
        api_key=get_elevenlabs_settings().elevenlabs_api_key,
        timeout=ELEVENLABS_CLIENT_TIMEOUT_SECONDS,
    )


async def synthesize_speech(
    *, text: str, voice_id: str | None = None, model_id: str | None = None
) -> bytes:
    """Convert text to speech and return the complete audio as bytes.

    convert() streams audio chunks over the wire, but the Interviewer's
    replies are short enough that buffering the complete clip before
    returning is simpler than plumbing a byte stream through the response.
    The TTS route returns these bytes as a single downloadable file.

    Raises ElevenLabsTransientError for retryable provider-side failures
    (network error, 5xx, 429 rate limit). Raises ElevenLabsRequestError,
    carrying ElevenLabs' status_code and message, for other ApiError
    failures (invalid voice_id, a plan-restricted voice, bad text, etc.)
    that will not succeed by retrying the same request unchanged.
    """
    settings = get_elevenlabs_settings()
    client = get_elevenlabs_client()
    resolved_voice_id = voice_id or settings.elevenlabs_voice_id
    resolved_model_id = model_id or settings.elevenlabs_model_id

    log = logger.bind(voice_id=resolved_voice_id, model_id=resolved_model_id)
    start_time = time.monotonic()
    log.info("elevenlabs.text_to_speech.start", text_length=len(text))

    try:
        chunks = [
            chunk
            async for chunk in client.text_to_speech.convert(
                resolved_voice_id,
                text=text,
                model_id=resolved_model_id,
                output_format=TTS_OUTPUT_FORMAT,
            )
        ]
    except Exception as exc:
        log.exception(
            "elevenlabs.text_to_speech.error",
            duration_seconds=time.monotonic() - start_time,
        )
        is_rate_limited = (
            isinstance(exc, ApiError)
            and exc.status_code == ELEVENLABS_RATE_LIMIT_STATUS_CODE
        )
        is_server_error = isinstance(exc, ApiError) and (
            exc.status_code is not None
            and exc.status_code >= httpx.codes.INTERNAL_SERVER_ERROR
        )
        if isinstance(exc, httpx.HTTPError) or is_rate_limited or is_server_error:
            raise ElevenLabsTransientError(str(exc)) from exc
        if isinstance(exc, ApiError):
            raise ElevenLabsRequestError(
                _api_error_message(exc),
                status_code=exc.status_code or httpx.codes.UNPROCESSABLE_ENTITY,
            ) from exc
        raise

    audio_bytes = b"".join(chunks)
    log.info(
        "elevenlabs.text_to_speech.success",
        duration_seconds=time.monotonic() - start_time,
        audio_bytes=len(audio_bytes),
    )
    return audio_bytes
