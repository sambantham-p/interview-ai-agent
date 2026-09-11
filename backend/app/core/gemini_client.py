import base64
from functools import lru_cache
from typing import Literal

from google import genai
from google.genai import interactions, types
from pydantic import BaseModel, Field

from app.constants.gemini import (
    GEMINI_CLIENT_TIMEOUT_MS,
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_MAX_DELAY_SECONDS,
)
from app.core.config import get_settings

MediaResolution = Literal["unspecified", "low", "medium", "high", "ultra_high"]


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
    contents: list[interactions.DocumentContentParam | interactions.TextContentParam],
    text_format: type[T],
    system_instruction: str,
    thinking_level: interactions.ThinkingLevel,
    seed: int | None = None,
) -> T:
    """Structured-output call via client.aio.interactions.create() - the
    Interactions API, Google's default as of June 2026 (generate_content,
    this wrapper's previous basis, is now documented as legacy).

    No .parsed shortcut here unlike generate_content - output_text is a
    raw JSON string, validated manually against text_format.

    system_instruction carries the task-level rules (what to extract, how
    to format it) via the API's own dedicated field - confirmed as a real
    top-level kwarg on interactions.create() by inspecting its signature
    (accepts **body: Any covering every CreateModelInteractionParam
    field). `contents`/`input` is reserved for the actual data being
    processed (e.g. the resume document) - previously the instructions
    were stuffed into a `text` content block sitting inside `input` next
    to the document, mixing task guidance with data instead of using the
    field built for it.

    Retries: interactions.create() ignores get_gemini_client()'s
    retry_options above - it has its own separate default (4 attempts,
    exponential backoff, capped at 30s total) that applies automatically
    with no config needed, confirmed by reading the SDK source.

    thinking_level has no default (every caller must decide, same
    reasoning as the removed enable_function_calling param) - left unset,
    it defaults to an adaptive, unpinned effort level, which contributes
    to run-to-run variance on the same input (some calls read a
    multi-column resume fully, some don't).

    seed is optional, defaulting to unset (the SDK's own natural
    default - normal, undetermined sampling). The Interactions API has
    no temperature/top_p/top_k to control sampling directly - confirmed
    via https://ai.google.dev/api/interactions-api - seed is Google's own
    documented mechanism for reproducible decoding instead. Pass a fixed
    value for calls where identical input should reliably produce
    identical output (e.g. resume extraction); leave unset for calls
    where natural variation is fine or desired (e.g. conversational
    turns).
    """
    client = get_gemini_client()
    generation_config: interactions.GenerationConfigParam = {
        "thinking_level": thinking_level
    }
    if seed is not None:
        generation_config["seed"] = seed
    interaction = await client.aio.interactions.create(
        model=model,
        input=contents,
        system_instruction=system_instruction,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": text_format.model_json_schema(),
        },
        generation_config=generation_config,
    )
    return text_format.model_validate_json(interaction.output_text)


class FileInputRequest(BaseModel):
    """Request DTO for build_file_input() - validated at runtime, unlike
    the SDK's own types below (no type-checker runs in this project).
    """

    file_bytes: bytes
    mime_type: str = Field(min_length=1)
    resolution: MediaResolution


def build_file_input(
    request: FileInputRequest,
) -> list[interactions.DocumentContentParam]:
    """Build Interactions API `input`: the file as a base64-encoded
    document content block. Task instructions go through
    extract_structured()'s system_instruction instead - input is for
    data, not task guidance.

    resolution has no default (every caller must decide, same "no silent
    default" convention as thinking_level) - Gemini 3 renders each PDF
    page as an image and processes it visually on top of native text
    extraction (which is free regardless of resolution); "high"/
    "ultra_high" spends real latency on visual fidelity a plain-text
    resume doesn't need, while "low" risks losing the layout cues a
    multi-column resume needs to read columns in the right order.
    """
    document: dict[str, str] = {
        "type": "document",
        "data": base64.b64encode(request.file_bytes).decode("utf-8"),
        "mime_type": request.mime_type,
        "resolution": request.resolution,
    }
    return [document]
