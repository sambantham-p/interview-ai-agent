import base64
from collections.abc import Iterator

import pytest
from pydantic import BaseModel, ValidationError
from pytest_mock import MockerFixture

from app.core.config import Settings
from app.core.gemini_client import (
    FileInputRequest,
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
    # (Note: interactions.create() below ignores this and uses its own
    # separate, already-sensible default retry policy instead - this
    # config still matters for any other endpoint that does respect it.)
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


def test_build_file_input_base64_encodes_the_file_as_a_document_block() -> None:
    # Task instructions no longer live here - they go through
    # extract_structured()'s system_instruction, so input carries only
    # the data (the document), not task guidance mixed into a text block.
    request = FileInputRequest(
        file_bytes=b"%PDF-1.4 fake pdf bytes",
        mime_type="application/pdf",
        resolution="medium",
    )

    content = build_file_input(request)

    assert len(content) == 1
    (document,) = content
    assert document["type"] == "document"
    assert document["mime_type"] == "application/pdf"
    assert document["data"] == base64.b64encode(b"%PDF-1.4 fake pdf bytes").decode(
        "utf-8"
    )


def test_build_file_input_includes_resolution_though_untyped_by_the_sdk() -> None:
    # resolution isn't a declared field on the SDK's own
    # DocumentContentParam in this version (only present for legacy
    # generate_content) - this asserts it still reaches the built dict,
    # since the actual wire request depends on it getting there.
    # (interactions.create()'s extra="allow" base model preserves it
    # from there through to the JSON body - see gemini_client.py.)
    request = FileInputRequest(
        file_bytes=b"data", mime_type="application/pdf", resolution="low"
    )

    (document,) = build_file_input(request)

    assert document["resolution"] == "low"


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


async def test_extract_structured_calls_interactions_create_and_returns_validated_result(
    mocker: MockerFixture,
) -> None:
    fake_interaction = mocker.MagicMock()
    fake_interaction.output_text = _FakeExtraction(value="parsed").model_dump_json()
    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        return_value=fake_interaction
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    result = await extract_structured(
        model="gemini-3.8-flash",
        contents=[{"type": "text", "text": "hi"}],
        text_format=_FakeExtraction,
        system_instruction="Extract the value.",
        thinking_level="high",
    )

    assert result == _FakeExtraction(value="parsed")
    fake_client.aio.interactions.create.assert_awaited_once()
    call_kwargs = fake_client.aio.interactions.create.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.8-flash"
    assert call_kwargs["input"] == [{"type": "text", "text": "hi"}]
    assert call_kwargs["system_instruction"] == "Extract the value."
    assert call_kwargs["response_format"]["mime_type"] == "application/json"
    assert (
        call_kwargs["response_format"]["schema"] == _FakeExtraction.model_json_schema()
    )
    assert call_kwargs["generation_config"] == {"thinking_level": "high"}


async def test_extract_structured_passes_seed_when_given(
    mocker: MockerFixture,
) -> None:
    # seed is the Interactions API's own documented reproducibility
    # mechanism (no temperature/top_p/top_k exist on this API) - callers
    # that need identical input to reliably produce identical output
    # (e.g. resume extraction) must pass it explicitly.
    fake_interaction = mocker.MagicMock()
    fake_interaction.output_text = _FakeExtraction(value="parsed").model_dump_json()
    fake_client = mocker.MagicMock()
    fake_client.aio.interactions.create = mocker.AsyncMock(
        return_value=fake_interaction
    )
    mocker.patch("app.core.gemini_client.get_gemini_client", return_value=fake_client)

    await extract_structured(
        model="gemini-3.8-flash",
        contents=[{"type": "text", "text": "hi"}],
        text_format=_FakeExtraction,
        system_instruction="Extract the value.",
        thinking_level="high",
        seed=42,
    )

    call_kwargs = fake_client.aio.interactions.create.call_args.kwargs
    assert call_kwargs["generation_config"] == {"thinking_level": "high", "seed": 42}


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
            contents=[{"type": "text", "text": "hi"}],
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
            contents=[{"type": "text", "text": "hi"}],
            text_format=_FakeExtraction,
            thinking_level="high",
        )
