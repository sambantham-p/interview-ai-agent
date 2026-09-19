import base64
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any, Literal, cast

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
from app.core.config import get_gemini_settings

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


def _is_transient(exc: Exception) -> bool:
    """A retryable Gemini-side failure - network error, 5xx, or a 429 rate
    limit. Shared by extract_structured() and run_tool_loop() so both
    classify errors the same way.
    """
    is_rate_limited = (
        isinstance(exc, ClientError) and exc.code == GEMINI_RATE_LIMIT_STATUS_CODE
    )
    return isinstance(exc, httpx.HTTPError | ServerError) or is_rate_limited


def _is_transient_interactions_error(exc: Exception) -> bool:
    """A retryable failure from the Interactions API - network error, 5xx,
    or a 429 rate limit. The SDK's error types for this API live in a
    private module and can't be imported safely, so this reads what they
    expose publicly instead: an HTTP `status_code` for a server response,
    or an `APIConnectionError` (which also covers `APITimeoutError`) in
    the class hierarchy when no response arrived at all.
    """
    status = getattr(exc, "status_code", None)
    is_retryable_status = isinstance(status, int) and (
        status == GEMINI_RATE_LIMIT_STATUS_CODE
        or status >= httpx.codes.INTERNAL_SERVER_ERROR
    )
    is_connection_error = any(
        cls.__name__ == "APIConnectionError" for cls in type(exc).__mro__
    )
    return (
        isinstance(exc, httpx.HTTPError) or is_retryable_status or is_connection_error
    )


def thinking_config_for(thinking_level: ThinkingLevel) -> types.ThinkingConfig:
    """Maps the plain ThinkingLevel literal to the SDK's exact enum
    shared by extract_structured() and any other caller that builds
    its own GenerateContentConfig.
    """
    return types.ThinkingConfig(thinking_level=_THINKING_LEVELS[thinking_level])


@lru_cache
def get_gemini_client() -> genai.Client:
    """Cached Gemini client, built lazily like get_engine() in db.py."""
    return genai.Client(
        api_key=get_gemini_settings().gemini_api_key,
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
    contents: list[types.Part] | list[types.Content],
    text_format: type[T],
    system_instruction: str,
    thinking_level: ThinkingLevel,
    seed: int | None = None,
    on_usage: Callable[[types.GenerateContentResponseUsageMetadata | None], None]
    | None = None,
) -> T:
    """Call generate_content and return the response validated as
    text_format.

    Logs a start line before the call and a success/error line after,
    both with the elapsed duration. Raises GeminiResponseParseError if
    the response doesn't match text_format, GeminiTransientError for a
    retryable Gemini-side failure (network error, 5xx, 429 rate limit).
    Any other error propagates unchanged.

    contents is either a single turn's Parts (wrapped into one Content -
    the resume/JD extraction shape) or a full multi-turn Content history
    (the Interviewer agent's shape, one Content per past turn) - passed
    straight through in the latter case so the model sees prior turns.

    thinking_level has no default - every caller must pick an effort
    level explicitly. seed is optional; pass a fixed value where
    identical input should reliably produce identical output (e.g.
    resume extraction), leave it unset where natural variation is fine.
    on_usage, if given, is called with the response's usage metadata
    (or None on failure) - lets the LLM Gateway capture token counts for
    its Postgres call-logging without this function's return type
    carrying usage on every caller's behalf.
    """
    client = get_gemini_client()
    log = logger.bind(model=model, text_format=text_format.__name__)
    start_time = time.monotonic()
    log.info("gemini.generate_content.start", thinking_level=thinking_level)

    gen_contents: types.Content | list[types.Content]
    if contents and isinstance(contents[0], types.Part):
        gen_contents = types.Content(parts=cast(list[types.Part], contents))
    else:
        gen_contents = cast(list[types.Content], contents)

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=cast(types.ContentListUnion, gen_contents),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=text_format,
                thinking_config=thinking_config_for(thinking_level),
                seed=seed,
            ),
        )
    except Exception as exc:
        log.exception(
            "gemini.generate_content.error",
            duration_seconds=time.monotonic() - start_time,
        )
        if on_usage is not None:
            on_usage(None)
        if _is_transient(exc):
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
        if on_usage is not None:
            on_usage(response.usage_metadata)
        raise GeminiResponseParseError(
            f"Gemini response did not parse into {text_format.__name__}: "
            f"{response.text!r}"
        )

    usage = response.usage_metadata
    if on_usage is not None:
        on_usage(usage)
    log.info(
        "gemini.generate_content.success",
        duration_seconds=duration_seconds,
        prompt_token_count=usage.prompt_token_count if usage else None,
        candidates_token_count=usage.candidates_token_count if usage else None,
        total_token_count=usage.total_token_count if usage else None,
    )
    return parsed


async def run_tool_loop(
    *,
    model: str,
    contents: list[types.Content],
    system_instruction: str,
    tools: list[types.Tool],
    tool_dispatch: dict[str, Callable[..., Awaitable[Any]]],
    thinking_level: ThinkingLevel,
    max_rounds: int,
    on_round: Callable[[int, types.GenerateContentResponse, float], Awaitable[None]]
    | None = None,
) -> list[types.Content]:
    """Run a bounded Gemini tool-calling loop.

    Sends the conversation to Gemini with the available tools, executes
    requested tool calls via `tool_dispatch`, feeds results back, and repeats
    until no more tool calls are requested or `max_rounds` is reached.

    Returns the accumulated history for the caller's final structured call.
    Tool errors are returned to Gemini; Gemini API errors propagate, with
    transient errors wrapped as `GeminiTransientError`.
    Calls `on_round` after each Gemini call to log the round.
    """
    client = get_gemini_client()
    history = list(contents)
    log = logger.bind(model=model)

    for round_number in range(max_rounds):
        round_start = time.monotonic()
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=cast(types.ContentListUnion, history),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=tools,
                    thinking_config=thinking_config_for(thinking_level),
                ),
            )
        except Exception as exc:
            log.exception("gemini.tool_loop.error", round=round_number)
            if _is_transient(exc):
                raise GeminiTransientError(str(exc)) from exc
            raise

        if on_round is not None:
            await on_round(round_number, response, time.monotonic() - round_start)

        if not response.candidates or response.candidates[0].content is None:
            block_reason = (
                response.prompt_feedback.block_reason
                if response.prompt_feedback
                else None
            )
            raise GeminiResponseParseError(
                f"Gemini returned no usable candidate (block_reason={block_reason})"
            )

        candidate_content = response.candidates[0].content
        function_calls = [
            part.function_call
            for part in (candidate_content.parts or [])
            if part.function_call is not None
        ]
        if not function_calls:
            log.info("gemini.tool_loop.no_more_calls", round=round_number)
            break

        history.append(candidate_content)
        response_parts = []
        for call in function_calls:
            args = call.args or {}
            log.info("gemini.tool_loop.calling", tool=call.name, round=round_number)
            try:
                tool_fn = tool_dispatch[call.name]
                result = await tool_fn(**args)
                result_payload = {"result": result}
            except Exception as exc:  # noqa: BLE001 - a tool failure must never crash the turn
                log.warning(
                    "gemini.tool_loop.tool_error",
                    tool=call.name,
                    round=round_number,
                    error=str(exc),
                )
                result_payload = {"error": str(exc)}
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name, response=result_payload
                )
            )
        history.append(types.Content(role="user", parts=response_parts))
    else:
        log.warning("gemini.tool_loop.max_rounds_reached", max_rounds=max_rounds)

    return history


async def _generate_plain(
    *,
    model: str,
    contents: types.ContentListUnion,
    config: types.GenerateContentConfig,
    log_event: str,
    on_usage: Callable[[types.GenerateContentResponseUsageMetadata | None], None]
    | None,
) -> types.GenerateContentResponse:
    """generate_content for calls that don't need structured output:
    timing/log lines, usage reporting, and Gemini-side failures mapped to
    GeminiTransientError, the same way extract_structured() does.
    """
    client = get_gemini_client()
    log = logger.bind(model=model)
    start_time = time.monotonic()
    log.info(f"{log_event}.start")
    try:
        response = await client.aio.models.generate_content(
            model=model, contents=contents, config=config
        )
    except Exception as exc:
        log.exception(
            f"{log_event}.error", duration_seconds=time.monotonic() - start_time
        )
        if on_usage is not None:
            on_usage(None)
        if _is_transient(exc):
            raise GeminiTransientError(str(exc)) from exc
        raise
    if on_usage is not None:
        on_usage(response.usage_metadata)
    log.info(f"{log_event}.success", duration_seconds=time.monotonic() - start_time)
    return response


EmbeddingTaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]


async def embed_content(
    *,
    model: str,
    text: str,
    task_type: EmbeddingTaskType,
    dimensions: int,
) -> list[float]:
    """Embeds one string with a Gemini embedding model, truncated to
    `dimensions` so it fits the pgvector column. Gemini-side failures map
    to GeminiTransientError, the same way extract_structured() does.
    """
    client = get_gemini_client()
    log = logger.bind(model=model)
    start_time = time.monotonic()
    try:
        response = await client.aio.models.embed_content(
            model=model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type, output_dimensionality=dimensions
            ),
        )
    except Exception as exc:
        log.exception(
            "embed_content.error", duration_seconds=time.monotonic() - start_time
        )
        if _is_transient(exc):
            raise GeminiTransientError(str(exc)) from exc
        raise
    (embedding,) = response.embeddings or []
    return list(embedding.values or [])


async def transcribe_audio(
    *,
    model: str,
    audio_bytes: bytes,
    mime_type: str,
    vocabulary: list[str] | None = None,
    on_usage: Callable[[types.GenerateContentResponseUsageMetadata | None], None]
    | None = None,
) -> str:
    """Speech-to-text with Gemini's dedicated transcription model, which is
    served only through the Interactions API. `vocabulary` biases
    recognition toward terms the audio is likely to contain (technical
    names, in an interview). Returns the transcript, or an empty string
    when the audio held no intelligible speech.
    """
    client = get_gemini_client()
    log = logger.bind(model=model)
    start_time = time.monotonic()
    log.info("gemini.transcribe_audio.start")

    generation_config: dict[str, Any] = {}
    if vocabulary:
        generation_config["transcription_config"] = {"custom_vocabulary": vocabulary}

    try:
        interaction = await client.aio.interactions.create(
            model=model,
            input=[
                {
                    "type": "audio",
                    "data": base64.b64encode(audio_bytes).decode(),
                    "mime_type": mime_type,
                }
            ],
            generation_config=generation_config or None,
        )
    except Exception as exc:
        log.exception(
            "gemini.transcribe_audio.error",
            duration_seconds=time.monotonic() - start_time,
        )
        if on_usage is not None:
            on_usage(None)
        if _is_transient_interactions_error(exc):
            raise GeminiTransientError(str(exc)) from exc
        raise

    usage = interaction.usage
    if on_usage is not None and usage is not None:
        on_usage(
            types.GenerateContentResponseUsageMetadata(
                prompt_token_count=usage.total_input_tokens,
                candidates_token_count=usage.total_output_tokens,
                total_token_count=usage.total_tokens,
            )
        )
    log.info(
        "gemini.transcribe_audio.success",
        duration_seconds=time.monotonic() - start_time,
    )
    return (interaction.output_text or "").strip()


async def generate_speech(
    *,
    model: str,
    text: str,
    voice_name: str,
    on_usage: Callable[[types.GenerateContentResponseUsageMetadata | None], None]
    | None = None,
) -> bytes:
    """Text-to-speech via a Gemini TTS model. Returns raw 16-bit mono PCM
    audio (the model's native output); the caller wraps it in a container.
    Raises GeminiResponseParseError if the response carries no audio.
    """
    response = await _generate_plain(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        ),
        log_event="gemini.generate_speech",
        on_usage=on_usage,
    )
    candidates = response.candidates or []
    parts = candidates[0].content.parts if candidates and candidates[0].content else []
    for part in parts or []:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data
    raise GeminiResponseParseError("Gemini TTS response contained no audio")


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
