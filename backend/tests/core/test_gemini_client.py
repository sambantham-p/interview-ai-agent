from collections.abc import Iterator

import httpx
import pytest
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, ValidationError
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.gemini_client import (
    FileInputRequest,
    GeminiResponseParseError,
    GeminiTransientError,
    MediaResolution,
    build_file_input,
    extract_structured,
    get_gemini_client,
)


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    get_gemini_client.cache_clear()
    yield
    get_gemini_client.cache_clear()


def test_get_gemini_client_uses_api_key_from_settings(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.gemini_client.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="key-from-settings",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )
    fake_client_cls = mocker.patch("app.core.gemini_client.genai.Client")

    get_gemini_client()

    assert fake_client_cls.call_args.kwargs["api_key"] == "key-from-settings"


def test_get_gemini_client_enables_retries(mocker: MockerFixture) -> None:
    # retry_options left unset means "never retry" per the SDK's own
    # docs - unlike OpenAI's SDK, which retries transient failures by
    # default. Must be set explicitly, not just present as a kwarg.
    mocker.patch(
        "app.core.gemini_client.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )
    fake_client_cls = mocker.patch("app.core.gemini_client.genai.Client")

    get_gemini_client()

    http_options = fake_client_cls.call_args.kwargs["http_options"]
    assert http_options.retry_options is not None
    assert http_options.retry_options.attempts >= 2


def test_get_gemini_client_is_cached(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.gemini_client.get_settings",
        return_value=Settings(
            database_url="postgresql://u:p@host/db",
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
        ),
    )

    assert get_gemini_client() is get_gemini_client()


def test_build_file_input_wraps_the_file_as_a_part_with_inline_data() -> None:
    # Task instructions no longer live here - they go through
    # extract_structured()'s system_instruction, so contents carries only
    # the data (the document), not task guidance mixed into a text block.
    request = FileInputRequest(
        file_bytes=b"%PDF-1.4 fake pdf bytes",
        mime_type="application/pdf",
        resolution="medium",
    )

    (part,) = build_file_input(request)

    assert isinstance(part, types.Part)
    assert part.inline_data is not None
    assert part.inline_data.mime_type == "application/pdf"
    assert part.inline_data.data == b"%PDF-1.4 fake pdf bytes"


@pytest.mark.parametrize(
    ("resolution", "expected_level"),
    [
        ("unspecified", types.PartMediaResolutionLevel.MEDIA_RESOLUTION_UNSPECIFIED),
        ("low", types.PartMediaResolutionLevel.MEDIA_RESOLUTION_LOW),
        ("medium", types.PartMediaResolutionLevel.MEDIA_RESOLUTION_MEDIUM),
        ("high", types.PartMediaResolutionLevel.MEDIA_RESOLUTION_HIGH),
        ("ultra_high", types.PartMediaResolutionLevel.MEDIA_RESOLUTION_ULTRA_HIGH),
    ],
)
def test_build_file_input_maps_resolution_to_the_sdks_exact_enum_level(
    resolution: MediaResolution, expected_level: types.PartMediaResolutionLevel
) -> None:
    # generate_content rejects the shorthand string directly (confirmed
    # against the live API: passing "high" for media_resolution.level
    # returns a 400 INVALID_ARGUMENT) - it needs the SDK's own
    # "MEDIA_RESOLUTION_HIGH"-style enum, not our plain-lowercase
    # MediaResolution literal. This asserts build_file_input() does that
    # translation rather than passing the shorthand straight through,
    # which is exactly the bug this migration fixes.
    request = FileInputRequest(
        file_bytes=b"data", mime_type="application/pdf", resolution=resolution
    )

    (part,) = build_file_input(request)

    assert part.media_resolution is not None
    assert part.media_resolution.level == expected_level


def test_file_input_request_rejects_blank_mime_type() -> None:
    with pytest.raises(ValidationError):
        FileInputRequest(file_bytes=b"data", mime_type="", resolution="medium")


def test_file_input_request_requires_resolution_to_be_specified() -> None:
    # No default - same "every caller must decide" convention as
    # thinking_level, since resolution is a real latency/fidelity
    # trade-off, not a safe universal default.
    with pytest.raises(ValidationError):
        FileInputRequest(file_bytes=b"data", mime_type="application/pdf")  # type: ignore[call-arg]


class _FakeExtraction(BaseModel):
    value: str


async def test_extract_structured_calls_generate_content_and_returns_parsed_result(
    mocker: MockerFixture,
) -> None:
    fake_response = mocker.MagicMock()
    fake_response.parsed = _FakeExtraction(value="parsed")
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    result = await extract_structured(
        model="gemini-3.8-flash",
        contents=[types.Part.from_text(text="hi")],
        text_format=_FakeExtraction,
        system_instruction="Extract the value.",
        thinking_level="high",
    )

    assert result == _FakeExtraction(value="parsed")
    fake_client.aio.models.generate_content.assert_awaited_once()
    call_kwargs = fake_client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.8-flash"
    assert call_kwargs["contents"] == types.Content(
        parts=[types.Part.from_text(text="hi")]
    )
    config = call_kwargs["config"]
    assert config.system_instruction == "Extract the value."
    assert config.response_mime_type == "application/json"
    assert config.response_schema is _FakeExtraction
    assert config.thinking_config.thinking_level == types.ThinkingLevel.HIGH
    assert config.seed is None


async def test_extract_structured_passes_seed_when_given(
    mocker: MockerFixture,
) -> None:
    fake_response = mocker.MagicMock()
    fake_response.parsed = _FakeExtraction(value="parsed")
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    await extract_structured(
        model="gemini-3.8-flash",
        contents=[types.Part.from_text(text="hi")],
        text_format=_FakeExtraction,
        system_instruction="Extract the value.",
        thinking_level="high",
        seed=42,
    )

    call_kwargs = fake_client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["config"].seed == 42


@pytest.mark.parametrize(
    "original",
    [
        httpx.ConnectError("gemini blew up"),
        ServerError(500, {"error": {"message": "gemini blew up"}}),
        ClientError(429, {"error": {"message": "gemini blew up"}}),
    ],
)
async def test_extract_structured_wraps_transient_gemini_failures(
    mocker: MockerFixture, original: Exception
) -> None:
    # A retryable Gemini-side failure (network error, 5xx, 429) is wrapped
    # into GeminiTransientError, which app/core/exception_handlers.py maps
    # to a 503 - callers don't need to know the SDK's own error types.
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(side_effect=original)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    log_spy = mocker.patch("app.core.gemini_client.logger")
    log_spy.bind.return_value = log_spy

    with pytest.raises(GeminiTransientError, match="gemini blew up") as exc_info:
        await extract_structured(
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
            thinking_level="high",
        )

    assert exc_info.value.__cause__ is original
    log_spy.exception.assert_called_once()
    assert log_spy.exception.call_args.args[0] == "gemini.generate_content.error"
    assert "duration_seconds" in log_spy.exception.call_args.kwargs


async def test_extract_structured_does_not_wrap_non_rate_limit_client_errors(
    mocker: MockerFixture,
) -> None:
    # A non-429 ClientError (bad request, expired key) won't be fixed by
    # retrying - left unwrapped so it surfaces as a genuine 500, not a
    # misleading "try again" or a misleading "bad resume file".
    original = ClientError(400, {"error": {"message": "invalid request"}})
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(side_effect=original)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(ClientError) as exc_info:
        await extract_structured(
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
            thinking_level="high",
        )

    assert exc_info.value is original


async def test_extract_structured_raises_when_response_does_not_parse_into_text_format(
    mocker: MockerFixture,
) -> None:
    # response.parsed is None (or the wrong type) when the model's output
    # doesn't validate against response_schema - this must surface as a
    # clear error rather than silently returning None to the caller.
    fake_response = mocker.MagicMock()
    fake_response.parsed = None
    fake_response.text = "not valid json"
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(GeminiResponseParseError, match="did not parse"):
        await extract_structured(
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
            thinking_level="high",
        )


async def test_extract_structured_requires_thinking_level_to_be_specified(
    mocker: MockerFixture,
) -> None:
    # No default, same reasoning as the removed enable_function_calling
    # param - every caller must consciously pick an effort level rather
    # than silently inheriting the SDK's adaptive default (the confirmed
    # cause of run-to-run non-determinism on identical resume input).
    fake_client = mocker.MagicMock()
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(TypeError):
        await extract_structured(  # type: ignore[call-arg]
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
        )


async def test_extract_structured_requires_system_instruction_to_be_specified(
    mocker: MockerFixture,
) -> None:
    # No default either - task guidance must always be explicit, never
    # silently omitted (which would leave the model with only a document
    # and a schema, no instructions on what to do with it).
    fake_client = mocker.MagicMock()
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(TypeError):
        await extract_structured(  # type: ignore[call-arg]
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            thinking_level="high",
        )
