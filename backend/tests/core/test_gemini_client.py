from collections.abc import Iterator
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, ValidationError
from pytest_mock import MockerFixture

from app.core.config import GeminiSettings
from app.core.gemini_client import (
    FileInputRequest,
    GeminiResponseParseError,
    GeminiTransientError,
    MediaResolution,
    build_file_input,
    extract_structured,
    get_gemini_client,
    run_tool_loop,
)


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    get_gemini_client.cache_clear()
    yield
    get_gemini_client.cache_clear()


def test_get_gemini_client_uses_api_key_from_settings(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.gemini_client.get_gemini_settings",
        return_value=GeminiSettings(
            gemini_api_key="key-from-settings",
            gemini_resume_parsing_model="gemini-3.8-flash",
            gemini_jd_parsing_model="gemini-3.8-flash",
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
        "app.core.gemini_client.get_gemini_settings",
        return_value=GeminiSettings(
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
            gemini_jd_parsing_model="gemini-3.8-flash",
        ),
    )
    fake_client_cls = mocker.patch("app.core.gemini_client.genai.Client")

    get_gemini_client()

    http_options = fake_client_cls.call_args.kwargs["http_options"]
    assert http_options.retry_options is not None
    assert http_options.retry_options.attempts >= 2


def test_get_gemini_client_is_cached(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.gemini_client.get_gemini_settings",
        return_value=GeminiSettings(
            gemini_api_key="test-key",
            gemini_resume_parsing_model="gemini-3.8-flash",
            gemini_jd_parsing_model="gemini-3.8-flash",
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


async def test_extract_structured_accepts_multi_turn_content_history(
    mocker: MockerFixture,
) -> None:
    # The Interviewer agent passes a full Content history (one per past
    # turn), not a single-turn Part list - this must go straight through
    # to generate_content rather than being re-wrapped into one Content.
    fake_response = mocker.MagicMock()
    fake_response.parsed = _FakeExtraction(value="parsed")
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    history = [
        types.Content(role="user", parts=[types.Part.from_text(text="turn 1")]),
        types.Content(role="model", parts=[types.Part.from_text(text="reply 1")]),
    ]

    await extract_structured(
        model="gemini-3.8-flash",
        contents=history,
        text_format=_FakeExtraction,
        system_instruction="Continue the conversation.",
        thinking_level="high",
    )

    call_kwargs = fake_client.aio.models.generate_content.call_args.kwargs
    assert call_kwargs["contents"] == history


async def test_extract_structured_calls_on_usage_with_usage_metadata_on_success(
    mocker: MockerFixture,
) -> None:
    fake_response = mocker.MagicMock()
    fake_response.parsed = _FakeExtraction(value="parsed")
    fake_response.usage_metadata = types.GenerateContentResponseUsageMetadata(
        total_token_count=9
    )
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    await extract_structured(
        model="gemini-3.8-flash",
        contents=[types.Part.from_text(text="hi")],
        text_format=_FakeExtraction,
        system_instruction="Extract the value.",
        thinking_level="high",
        on_usage=on_usage,
    )

    on_usage.assert_called_once_with(fake_response.usage_metadata)


async def test_extract_structured_calls_on_usage_with_none_on_transient_failure(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=httpx.ConnectError("down")
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    with pytest.raises(GeminiTransientError):
        await extract_structured(
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
            thinking_level="high",
            on_usage=on_usage,
        )

    on_usage.assert_called_once_with(None)


async def test_extract_structured_calls_on_usage_with_real_usage_on_parse_failure(
    mocker: MockerFixture,
) -> None:
    """A parse failure means the response didn't match text_format, not
    that the Gemini call itself failed - real usage_metadata is still
    available on the response and must still reach the gateway's logging,
    not be discarded as if the call never happened.
    """
    fake_response = mocker.MagicMock()
    fake_response.parsed = None
    fake_response.text = "not valid json"
    fake_response.usage_metadata = types.GenerateContentResponseUsageMetadata(
        total_token_count=7
    )
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=fake_response
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    with pytest.raises(GeminiResponseParseError):
        await extract_structured(
            model="gemini-3.8-flash",
            contents=[types.Part.from_text(text="hi")],
            text_format=_FakeExtraction,
            system_instruction="Extract the value.",
            thinking_level="high",
            on_usage=on_usage,
        )

    on_usage.assert_called_once_with(fake_response.usage_metadata)


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


def _content_with_text(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part.from_text(text=text)])


def _content_with_function_call(name: str, args: dict) -> types.Content:
    return types.Content(
        role="model",
        parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
    )


def _response_with_content(content: types.Content) -> MagicMock:
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


async def test_run_tool_loop_returns_history_unchanged_when_no_function_calls(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=_response_with_content(_content_with_text("no tools needed"))
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    original_history = [
        types.Content(role="user", parts=[types.Part.from_text(text="hi")])
    ]

    result = await run_tool_loop(
        model="gemini-3.8-flash",
        contents=list(original_history),
        system_instruction="You have tools.",
        tools=[],
        tool_dispatch={},
        thinking_level="medium",
        max_rounds=4,
    )

    assert result == original_history
    fake_client.aio.models.generate_content.assert_awaited_once()


async def test_run_tool_loop_executes_tool_and_feeds_result_back(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_tool = mocker.AsyncMock(return_value={"repos": ["a", "b"]})
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=[
            _response_with_content(
                _content_with_function_call("list_repos", {"username": "octocat"})
            ),
            _response_with_content(_content_with_text("done")),
        ]
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    result = await run_tool_loop(
        model="gemini-3.8-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        system_instruction="You have tools.",
        tools=[],
        tool_dispatch={"list_repos": fake_tool},
        thinking_level="medium",
        max_rounds=4,
    )

    fake_tool.assert_awaited_once_with(username="octocat")
    assert fake_client.aio.models.generate_content.await_count == 2
    # original + model's function-call turn + the function-response turn
    assert len(result) == 3
    function_response_part = result[-1].parts[0]
    assert function_response_part.function_response.name == "list_repos"
    assert function_response_part.function_response.response == {
        "result": {"repos": ["a", "b"]}
    }


async def test_run_tool_loop_feeds_error_back_instead_of_raising(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_tool = mocker.AsyncMock(side_effect=RuntimeError("repo not found"))
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=[
            _response_with_content(
                _content_with_function_call("list_repos", {"username": "octocat"})
            ),
            _response_with_content(_content_with_text("done")),
        ]
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    result = await run_tool_loop(
        model="gemini-3.8-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        system_instruction="You have tools.",
        tools=[],
        tool_dispatch={"list_repos": fake_tool},
        thinking_level="medium",
        max_rounds=4,
    )

    function_response_part = result[-1].parts[0]
    assert function_response_part.function_response.response == {
        "error": "repo not found"
    }


async def test_run_tool_loop_stops_at_max_rounds_without_raising(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_tool = mocker.AsyncMock(return_value="x")
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        return_value=_response_with_content(
            _content_with_function_call("list_repos", {"username": "octocat"})
        )
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    result = await run_tool_loop(
        model="gemini-3.8-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        system_instruction="You have tools.",
        tools=[],
        tool_dispatch={"list_repos": fake_tool},
        thinking_level="medium",
        max_rounds=2,
    )

    assert fake_client.aio.models.generate_content.await_count == 2
    # original + 2 rounds of (model call + function response)
    assert len(result) == 1 + 2 * 2


async def test_run_tool_loop_wraps_transient_generate_content_failures(
    mocker: MockerFixture,
) -> None:
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=ServerError(500, {"error": {"message": "gemini blew up"}})
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(GeminiTransientError, match="gemini blew up"):
        await run_tool_loop(
            model="gemini-3.8-flash",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="You have tools.",
            tools=[],
            tool_dispatch={},
            thinking_level="medium",
            max_rounds=4,
        )


async def test_run_tool_loop_does_not_wrap_non_transient_failures(
    mocker: MockerFixture,
) -> None:
    original = ClientError(400, {"error": {"message": "bad request"}})
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(side_effect=original)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(ClientError) as exc_info:
        await run_tool_loop(
            model="gemini-3.8-flash",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="You have tools.",
            tools=[],
            tool_dispatch={},
            thinking_level="medium",
            max_rounds=4,
        )

    assert exc_info.value is original


async def test_run_tool_loop_raises_parse_error_when_no_candidates(
    mocker: MockerFixture,
) -> None:
    response = MagicMock()
    response.candidates = []
    response.prompt_feedback = MagicMock(block_reason="SAFETY")
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(GeminiResponseParseError, match="SAFETY"):
        await run_tool_loop(
            model="gemini-3.8-flash",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="You have tools.",
            tools=[],
            tool_dispatch={},
            thinking_level="medium",
            max_rounds=4,
        )


async def test_run_tool_loop_raises_parse_error_when_candidate_has_no_content(
    mocker: MockerFixture,
) -> None:
    candidate = MagicMock()
    candidate.content = None
    response = MagicMock()
    response.candidates = [candidate]
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(GeminiResponseParseError):
        await run_tool_loop(
            model="gemini-3.8-flash",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="You have tools.",
            tools=[],
            tool_dispatch={},
            thinking_level="medium",
            max_rounds=4,
        )


async def test_run_tool_loop_calls_on_round_after_each_generate_call(
    mocker: MockerFixture,
) -> None:
    candidate = MagicMock()
    candidate.content = types.Content(
        role="model", parts=[types.Part.from_text(text="done")]
    )
    response = MagicMock()
    response.candidates = [candidate]
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_round = mocker.AsyncMock()

    await run_tool_loop(
        model="gemini-3.8-flash",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        system_instruction="You have tools.",
        tools=[],
        tool_dispatch={},
        thinking_level="medium",
        max_rounds=4,
        on_round=on_round,
    )

    assert on_round.await_count == 1
    assert on_round.await_args.args[0] == 0
    assert on_round.await_args.args[1] is response


class _StatusError(Exception):
    def __init__(self, status_code: object) -> None:
        super().__init__("status error")
        self.status_code = status_code


class APIConnectionError(Exception):
    pass


class APITimeoutError(APIConnectionError):
    pass


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_StatusError(429), True),
        (_StatusError(503), True),
        (_StatusError(400), False),
        (_StatusError("oops"), False),
        (httpx.ConnectError("down"), True),
        (APIConnectionError("no response"), True),
        (APITimeoutError("timed out"), True),
        (ValueError("plain"), False),
    ],
)
def test_is_transient_interactions_error_classification(
    exc: Exception, expected: bool
) -> None:
    from app.core.gemini_client import _is_transient_interactions_error

    assert _is_transient_interactions_error(exc) is expected


def test_thinking_config_for_maps_each_level() -> None:
    from app.core.gemini_client import thinking_config_for

    assert thinking_config_for("high").thinking_level == types.ThinkingLevel.HIGH
    assert thinking_config_for("minimal").thinking_level == types.ThinkingLevel.MINIMAL


def _text_response(text: str = "hello") -> MagicMock:
    response = MagicMock()
    response.usage_metadata = "usage"
    response.candidates = [MagicMock()]
    return response


async def test_generate_plain_reports_usage_on_success(mocker: MockerFixture) -> None:
    from app.core.gemini_client import _generate_plain

    response = _text_response()
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    result = await _generate_plain(
        model="m",
        contents="hi",
        config=types.GenerateContentConfig(),
        log_event="test.plain",
        on_usage=on_usage,
    )

    assert result is response
    on_usage.assert_called_once_with("usage")


async def test_generate_plain_wraps_transient_errors_and_reports_none_usage(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import _generate_plain

    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=ServerError(500, {"error": {"message": "boom"}})
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    with pytest.raises(GeminiTransientError):
        await _generate_plain(
            model="m",
            contents="hi",
            config=types.GenerateContentConfig(),
            log_event="test.plain",
            on_usage=on_usage,
        )

    on_usage.assert_called_once_with(None)


async def test_generate_plain_reraises_non_transient_errors(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import _generate_plain

    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(
        side_effect=ValueError("bad")
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(ValueError, match="bad"):
        await _generate_plain(
            model="m",
            contents="hi",
            config=types.GenerateContentConfig(),
            log_event="test.plain",
            on_usage=None,
        )


def _interaction(text: str | None = " hello there ", usage: object | None = None):
    interaction = MagicMock()
    interaction.output_text = text
    interaction.usage = usage
    return interaction


async def test_transcribe_audio_returns_stripped_text_and_sends_vocabulary(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import transcribe_audio

    usage = MagicMock(total_input_tokens=10, total_output_tokens=5, total_tokens=15)
    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        return_value=_interaction(usage=usage)
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    text = await transcribe_audio(
        model="stt",
        audio_bytes=b"abc",
        mime_type="audio/webm",
        vocabulary=["FastAPI"],
        on_usage=on_usage,
    )

    assert text == "hello there"
    kwargs = fake_client.aio.interactions.create.call_args.kwargs
    assert kwargs["input"][0]["mime_type"] == "audio/webm"
    assert kwargs["generation_config"] == {
        "transcription_config": {"custom_vocabulary": ["FastAPI"]}
    }
    reported = on_usage.call_args.args[0]
    assert reported.prompt_token_count == 10
    assert reported.total_token_count == 15


async def test_transcribe_audio_returns_empty_string_when_no_speech(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import transcribe_audio

    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        return_value=_interaction(text=None)
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    text = await transcribe_audio(model="stt", audio_bytes=b"a", mime_type="audio/webm")

    assert text == ""
    assert (
        fake_client.aio.interactions.create.call_args.kwargs["generation_config"]
        is None
    )


async def test_transcribe_audio_wraps_transient_errors(mocker: MockerFixture) -> None:
    from app.core.gemini_client import transcribe_audio

    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        side_effect=_StatusError(503)
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)
    on_usage = mocker.MagicMock()

    with pytest.raises(GeminiTransientError):
        await transcribe_audio(
            model="stt", audio_bytes=b"a", mime_type="audio/webm", on_usage=on_usage
        )

    on_usage.assert_called_once_with(None)


async def test_transcribe_audio_reraises_non_transient_errors(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import transcribe_audio

    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        side_effect=_StatusError(400)
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(_StatusError):
        await transcribe_audio(model="stt", audio_bytes=b"a", mime_type="audio/webm")


async def test_generate_speech_returns_pcm_bytes(mocker: MockerFixture) -> None:
    from app.core.gemini_client import generate_speech

    part = MagicMock()
    part.inline_data.data = b"pcm-bytes"
    response = MagicMock()
    response.usage_metadata = None
    response.candidates = [MagicMock(content=MagicMock(parts=[part]))]
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    audio = await generate_speech(model="tts", text="Hello", voice_name="Kore")

    assert audio == b"pcm-bytes"


async def test_generate_speech_raises_when_no_audio_in_response(
    mocker: MockerFixture,
) -> None:
    from app.core.gemini_client import generate_speech

    response = MagicMock()
    response.usage_metadata = None
    response.candidates = []
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    with pytest.raises(GeminiResponseParseError):
        await generate_speech(model="tts", text="Hello", voice_name="Kore")


async def test_generate_speech_skips_parts_without_audio(mocker: MockerFixture) -> None:
    from app.core.gemini_client import generate_speech

    text_part = MagicMock()
    text_part.inline_data = None
    audio_part = MagicMock()
    audio_part.inline_data.data = b"pcm"
    response = MagicMock()
    response.usage_metadata = None
    response.candidates = [MagicMock(content=MagicMock(parts=[text_part, audio_part]))]
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content = mocker.AsyncMock(return_value=response)
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    assert await generate_speech(model="tts", text="Hi", voice_name="Kore") == b"pcm"
