import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, cast

import structlog
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.voice import TTS_TASK
from app.core.config import get_elevenlabs_settings, get_gateway_settings
from app.core.db import get_session_factory
from app.core.elevenlabs_client import synthesize_speech as _synthesize_speech
from app.core.gemini_client import (
    ThinkingLevel,
    extract_structured,
    get_gemini_client,
    run_tool_loop,
    thinking_config_for,
)
from app.core.session_lookup import get_interview_session_or_404
from app.models.llm_call import LLMCall

logger = structlog.get_logger(__name__)

# Caps each llm_calls row to prevent unbounded growth from long
# multi-turn transcripts. The full transcript is stored in the
# InterviewSession.transcript.
_MAX_LOGGED_CHARS = 8_000


def _truncate(text: str) -> str:
    if len(text) <= _MAX_LOGGED_CHARS:
        return text
    return text[:_MAX_LOGGED_CHARS] + "...[truncated]"


def _contents_as_text(contents: list[types.Part] | list[types.Content]) -> str:
    """Flatten either shape extract_structured() accepts (single-turn
    Parts or multi-turn Content history) into plain text for logging.
    """
    if contents and isinstance(contents[0], types.Content):
        history = cast(list[types.Content], contents)
        parts = [p for c in history for p in (c.parts or [])]
    else:
        parts = cast(list[types.Part], contents)
    return "\n".join(p.text for p in parts if p.text)


async def _log_call(
    *,
    task: str,
    model: str,
    session_id: int | None,
    prompt: str,
    response: str,
    latency_seconds: float,
    usage: types.GenerateContentResponseUsageMetadata | None,
    error: str | None,
    extra: dict | None = None,
) -> None:
    """Every LLM Gateway call logs here, success or failure - this is
    the only place that sees which agent role is driving cost/latency,
    and the mechanism behind the per-interview voice-cost cap.

    Deliberately uses its own DB session rather than the caller's.
    Using a separate session prevents logging from committing or releasing locks
    held by the caller's transaction. Logging failures are swallowed so they
    never fail an otherwise successful interview turn.
    """
    call = LLMCall(
        task=task,
        model=model,
        session_id=session_id,
        prompt=_truncate(prompt),
        response=_truncate(response),
        prompt_token_count=usage.prompt_token_count if usage else None,
        candidates_token_count=usage.candidates_token_count if usage else None,
        total_token_count=usage.total_token_count if usage else None,
        latency_seconds=latency_seconds,
        error=error,
        extra=extra
        if extra is not None
        else {
            "cached_content_token_count": (
                usage.cached_content_token_count if usage else None
            )
        },
    )
    try:
        async with get_session_factory()() as log_db:
            log_db.add(call)
            await log_db.commit()
    except Exception:
        logger.exception("llm_gateway.log_call.failed", task=task)


async def generate_structured[T: BaseModel](
    *,
    task: str,
    contents: list[types.Part] | list[types.Content],
    text_format: type[T],
    system_instruction: str,
    thinking_level: ThinkingLevel,
    session_id: int | None,
    db: AsyncSession,
    seed: int | None = None,
) -> T:
    """The LLM Gateway's structured-output entry point: resolves the
    model for `task` from the routing config, calls through to
    extract_structured(), and logs the call (prompt, response, latency,
    token usage) to Postgres regardless of outcome.

    Every agent call - the Interviewer, the Judges - goes through this,
    not extract_structured() directly, so routing/logging stay in one
    place instead of being reimplemented per agent.
    """
    model = get_gateway_settings().model_for_task(task)
    prompt_text = (
        f"[system]\n{system_instruction}\n\n[contents]\n{_contents_as_text(contents)}"
    )
    start_time = time.monotonic()

    captured_usage: types.GenerateContentResponseUsageMetadata | None = None

    def _capture_usage(
        usage: types.GenerateContentResponseUsageMetadata | None,
    ) -> None:
        nonlocal captured_usage
        captured_usage = usage

    try:
        result = await extract_structured(
            model=model,
            contents=contents,
            text_format=text_format,
            system_instruction=system_instruction,
            thinking_level=thinking_level,
            seed=seed,
            on_usage=_capture_usage,
        )
    except Exception as exc:
        await _log_call(
            task=task,
            model=model,
            session_id=session_id,
            prompt=prompt_text,
            response="",
            latency_seconds=time.monotonic() - start_time,
            usage=captured_usage,
            error=str(exc),
        )
        raise

    await _log_call(
        task=task,
        model=model,
        session_id=session_id,
        prompt=prompt_text,
        response=result.model_dump_json(),
        latency_seconds=time.monotonic() - start_time,
        usage=captured_usage,
        error=None,
    )
    return result


async def generate_structured_with_tools[T: BaseModel](
    *,
    task: str,
    contents: list[types.Content],
    text_format: type[T],
    system_instruction: str,
    thinking_level: ThinkingLevel,
    tools: list[types.Tool],
    tool_dispatch: dict[str, Callable[..., Awaitable[Any]]],
    max_rounds: int,
    session_id: int | None,
    db: AsyncSession,
) -> T:
    """Same job as generate_structured(), for a turn where the model may
    need to call tools first (currently: GitHub lookups in Phase 2). Runs
    run_tool_loop() to let the model gather tool results, each round
    logged to Postgres, then makes one final generate_structured() call
    against the accumulated history for the actual structured output -
    Gemini can't return both function calls and a response_schema payload
    in one call, so this is genuinely two phases, not a parameter tweak.
    """
    model = get_gateway_settings().model_for_task(task)

    async def _log_round(
        round_number: int,
        response: types.GenerateContentResponse,
        latency_seconds: float,
    ) -> None:
        await _log_call(
            task=f"{task}_tool_call",
            model=model,
            session_id=session_id,
            prompt=f"[tool loop round {round_number}]",
            response=response.text or "<function call>",
            latency_seconds=latency_seconds,
            usage=response.usage_metadata,
            error=None,
        )

    history = await run_tool_loop(
        model=model,
        contents=contents,
        system_instruction=system_instruction,
        tools=tools,
        tool_dispatch=tool_dispatch,
        thinking_level=thinking_level,
        max_rounds=max_rounds,
        on_round=_log_round,
    )

    return await generate_structured(
        task=task,
        contents=history,
        text_format=text_format,
        system_instruction=system_instruction,
        thinking_level=thinking_level,
        session_id=session_id,
        db=db,
    )


async def stream_text(
    *,
    task: str,
    contents: list[types.Content],
    system_instruction: str,
    thinking_level: ThinkingLevel,
    session_id: int | None,
    db: AsyncSession,
) -> AsyncIterator[str]:
    """The LLM Gateway's streaming entry point: yields response text
    chunk-by-chunk as Gemini produces them, then logs the accumulated
    call once the stream ends.

    Used where token-by-token delivery matters more than a structured
    judgment payload (e.g. phase 7's free-form candidate Q&A) - the main
    phase-turn path uses generate_structured() instead, since hint/
    red-flag/phase-transition decisions need structured fields Gemini's
    streaming JSON mode can't reliably deliver mid-stream.
    """
    model = get_gateway_settings().model_for_task(task)
    client = get_gemini_client()
    prompt_text = (
        f"[system]\n{system_instruction}\n\n[contents]\n{_contents_as_text(contents)}"
    )
    start_time = time.monotonic()

    chunks: list[str] = []
    usage: types.GenerateContentResponseUsageMetadata | None = None
    error: str | None = None
    try:
        stream = await client.aio.models.generate_content_stream(
            model=model,
            contents=cast(types.ContentListUnion, contents),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                thinking_config=thinking_config_for(thinking_level),
            ),
        )
        async for chunk in stream:
            if chunk.text:
                chunks.append(chunk.text)
                yield chunk.text
            if chunk.usage_metadata:
                usage = chunk.usage_metadata
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        await _log_call(
            task=task,
            model=model,
            session_id=session_id,
            prompt=prompt_text,
            response="".join(chunks),
            latency_seconds=time.monotonic() - start_time,
            usage=usage,
            error=error,
        )


async def synthesize_speech(
    *,
    text: str,
    session_id: int | None,
    user_id: str | None,
    db: AsyncSession,
) -> bytes:
    """LLM Gateway entry point for text-to-speech using ElevenLabs.

    Calls ElevenLabs and logs the call to the same llm_calls table used for
    Gemini calls. Reusing llm_calls (task="tts", character count in `extra`,
    no token counts) is deliberate: it provides the per-interview voice
    usage data needed to enforce the voice cost cap by summing character
    counts logged under this session_id.

    When `session_id` is given, `user_id` must belong to that session -
    enforced by get_interview_session_or_404 the same way as every other
    session-scoped endpoint, so one candidate can't synthesize speech
    against another's interview.
    """
    if session_id is not None:
        assert user_id is not None  # nosec B101
        await get_interview_session_or_404(session_id, db, user_id=user_id)

    settings = get_elevenlabs_settings()
    model = settings.elevenlabs_model_id
    start_time = time.monotonic()
    character_count = len(text)

    try:
        audio_bytes = await _synthesize_speech(text=text)
    except Exception as exc:
        await _log_call(
            task=TTS_TASK,
            model=model,
            session_id=session_id,
            prompt=text,
            response="",
            latency_seconds=time.monotonic() - start_time,
            usage=None,
            error=str(exc),
            extra={"character_count": character_count},
        )
        raise

    await _log_call(
        task=TTS_TASK,
        model=model,
        session_id=session_id,
        prompt=text,
        response=f"<audio: {len(audio_bytes)} bytes>",
        latency_seconds=time.monotonic() - start_time,
        usage=None,
        error=None,
        extra={"character_count": character_count},
    )
    return audio_bytes
