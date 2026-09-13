import time
from collections.abc import AsyncIterator
from typing import cast

import structlog
from google.genai import types
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_gateway_settings
from app.core.gemini_client import (
    ThinkingLevel,
    extract_structured,
    get_gemini_client,
    thinking_config_for,
)
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
    db: AsyncSession,
    *,
    task: str,
    model: str,
    session_id: int | None,
    prompt: str,
    response: str,
    latency_seconds: float,
    usage: types.GenerateContentResponseUsageMetadata | None,
    error: str | None,
) -> None:
    """Every LLM Gateway call logs here, success or failure - this is
    the only place that sees which agent role is driving cost/latency,
    and the mechanism behind the per-interview voice-cost cap.
    """
    db.add(
        LLMCall(
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
            extra={
                "cached_content_token_count": (
                    usage.cached_content_token_count if usage else None
                )
            },
        )
    )
    await db.commit()


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
            db,
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
        db,
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
            db,
            task=task,
            model=model,
            session_id=session_id,
            prompt=prompt_text,
            response="".join(chunks),
            latency_seconds=time.monotonic() - start_time,
            usage=usage,
            error=error,
        )
