import time
from functools import lru_cache
from typing import Literal

import httpx
import structlog
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, Field

from app.constants.gemini import (
    GEMINI_CLIENT_TIMEOUT_MS,
    GEMINI_RATE_LIMIT_STATUS_CODE,
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_MAX_DELAY_SECONDS,
)
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class GeminiTransientError(Exception):
    """A retryable Gemini-side failure (network error, 5xx, 429 rate
    limit) - not the caller's fault. Callers don't need to inspect the
    original SDK error; app/core/exception_handlers.py maps this straight
    to a 503.
    """


class GeminiResponseParseError(Exception):
    """Gemini responded but the output didn't match the requested
    text_format. Distinct from GeminiTransientError since retrying the
    same input won't fix a schema mismatch.
    """


MediaResolution = Literal["unspecified", "low", "medium", "high", "ultra_high"]
ThinkingLevel = Literal["minimal", "low", "medium", "high"]

_MEDIA_RESOLUTION_LEVELS: dict[MediaResolution, types.PartMediaResolutionLevel] = {
    "unspecified": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_UNSPECIFIED,
    "low": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_LOW,
    "medium": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM,
    "high": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_HIGH,
    "ultra_high": types.PartMediaResolutionLevel.MEDIA_RESOLUTION_ULTRA_HIGH,
}

_THINKING_LEVELS: dict[ThinkingLevel, types.ThinkingLevel] = {
    "minimal": types.ThinkingLevel.MINIMAL,
    "low": types.ThinkingLevel.LOW,
    "medium": types.ThinkingLevel.MEDIUM,
    "high": types.ThinkingLevel.HIGH,
}


@lru_cache
def get_gemini_client() -> genai.Client:
    """Cached Gemini client, built lazily like get_engine() in db.py."""
    return genai.Client(
        api_key=get_settings().gemini_api_key,
        http_options=types.HttpOptions(
            timeout=GEMINI_CLIENT_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(
                attempts=GEMINI_RETRY_ATTEMPTS,
                max_delay=GEMINI_RETRY_MAX_DELAY_SECONDS,
            ),
        ),
    )


async def extract_structured[T: BaseModel](
    *,
    model: str,
    contents: list[types.Part],
    text_format: type[T],
    system_instruction: str,
    thinking_level: ThinkingLevel,
    seed: int | None = None,
) -> T:
    """Call generate_content and return the response validated as
    text_format.

    Logs a start line before the call and a success/error line after,
    both with the elapsed duration. Raises GeminiResponseParseError if
    the response doesn't match text_format, GeminiTransientError for a
    retryable Gemini-side failure (network error, 5xx, 429 rate limit).
    Any other error propagates unchanged.

    thinking_level has no default - every caller must pick an effort
    level explicitly. seed is optional; pass a fixed value where
    identical input should reliably produce identical output (e.g.
    resume extraction), leave it unset where natural variation is fine.
    """
    client = get_gemini_client()
    log = logger.bind(model=model, text_format=text_format.__name__)
    start_time = time.monotonic()
    log.info("gemini.generate_content.start", thinking_level=thinking_level)

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=types.Content(parts=contents),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=text_format,
                thinking_config=types.ThinkingConfig(
                    thinking_level=_THINKING_LEVELS[thinking_level]
                ),
                seed=seed,
            ),
        )
    except Exception as exc:
        log.exception(
            "gemini.generate_content.error",
            duration_seconds=time.monotonic() - start_time,
        )
        is_rate_limited = (
            isinstance(exc, ClientError) and exc.code == GEMINI_RATE_LIMIT_STATUS_CODE
        )
        if isinstance(exc, httpx.HTTPError | ServerError) or is_rate_limited:
            raise GeminiTransientError(str(exc)) from exc
        raise

    duration_seconds = time.monotonic() - start_time
    parsed = response.parsed
    if not isinstance(parsed, text_format):
        log.error(
            "gemini.generate_content.parse_failed",
            duration_seconds=duration_seconds,
            response_text=response.text,
        )
        raise GeminiResponseParseError(
            f"Gemini response did not parse into {text_format.__name__}: "
            f"{response.text!r}"
        )

    usage = response.usage_metadata
    log.info(
        "gemini.generate_content.success",
        duration_seconds=duration_seconds,
        prompt_token_count=usage.prompt_token_count if usage else None,
        candidates_token_count=usage.candidates_token_count if usage else None,
        total_token_count=usage.total_token_count if usage else None,
    )
    return parsed


class FileInputRequest(BaseModel):
    """Request DTO for build_file_input(), validated at runtime."""

    file_bytes: bytes
    mime_type: str = Field(min_length=1)
    resolution: MediaResolution


def build_file_input(request: FileInputRequest) -> list[types.Part]:
    """Build a generate_content Part from file bytes, with resolution
    mapped to the SDK's MediaResolution enum.

    resolution has no default: higher resolution costs latency but
    preserves layout cues a multi-column resume needs to read correctly.
    """
    return [
        types.Part.from_bytes(
            data=request.file_bytes,
            mime_type=request.mime_type,
            media_resolution=_MEDIA_RESOLUTION_LEVELS[request.resolution],
        )
    ]
