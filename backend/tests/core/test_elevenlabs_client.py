from collections.abc import Iterator

import httpx
import pytest
from elevenlabs.core.api_error import ApiError
from pytest_mock import MockerFixture

from app.core.config import ElevenLabsSettings
from app.core.elevenlabs_client import (
    ElevenLabsRequestError,
    ElevenLabsTransientError,
    get_elevenlabs_client,
    synthesize_speech,
)


@pytest.fixture(autouse=True)
def _clear_client_cache() -> Iterator[None]:
    get_elevenlabs_client.cache_clear()
    yield
    get_elevenlabs_client.cache_clear()


def _mock_settings(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_settings",
        return_value=ElevenLabsSettings(
            elevenlabs_api_key="test-key",
            elevenlabs_voice_id="voice-1",
            elevenlabs_model_id="eleven_multilingual_v2",
        ),
    )


def test_get_elevenlabs_client_uses_api_key_from_settings(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    fake_client_cls = mocker.patch("app.core.elevenlabs_client.AsyncElevenLabs")

    get_elevenlabs_client()

    assert fake_client_cls.call_args.kwargs["api_key"] == "test-key"


def test_get_elevenlabs_client_is_cached(mocker: MockerFixture) -> None:
    _mock_settings(mocker)

    assert get_elevenlabs_client() is get_elevenlabs_client()


async def test_synthesize_speech_returns_joined_audio_bytes(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)

    async def fake_convert(voice_id, **kwargs):
        for chunk in (b"chunk1", b"chunk2"):
            yield chunk

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    result = await synthesize_speech(text="hello there")

    assert result == b"chunk1chunk2"


async def test_synthesize_speech_uses_voice_and_model_from_settings_by_default(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    captured = {}

    async def fake_convert(voice_id, **kwargs):
        captured["voice_id"] = voice_id
        captured["model_id"] = kwargs["model_id"]
        return
        yield  # pragma: no cover - makes this an async generator

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    await synthesize_speech(text="hello")

    assert captured["voice_id"] == "voice-1"
    assert captured["model_id"] == "eleven_multilingual_v2"


async def test_synthesize_speech_prefers_explicit_voice_and_model_over_settings(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    captured = {}

    async def fake_convert(voice_id, **kwargs):
        captured["voice_id"] = voice_id
        captured["model_id"] = kwargs["model_id"]
        return
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    await synthesize_speech(
        text="hello", voice_id="other-voice", model_id="other-model"
    )

    assert captured["voice_id"] == "other-voice"
    assert captured["model_id"] == "other-model"


@pytest.mark.parametrize(
    "original",
    [
        httpx.ConnectError("elevenlabs blew up"),
        ApiError(status_code=500, body="server error"),
        ApiError(status_code=429, body="rate limited"),
    ],
)
async def test_synthesize_speech_wraps_transient_failures(
    mocker: MockerFixture, original: Exception
) -> None:
    _mock_settings(mocker)

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover - makes this an async generator

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(ElevenLabsTransientError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value.__cause__ is original


async def test_synthesize_speech_wraps_non_transient_api_errors_with_status_and_message(
    mocker: MockerFixture,
) -> None:
    # A 4xx that isn't the rate-limit code (e.g. invalid voice_id, a
    # plan-restricted voice, bad text) won't be fixed by retrying -
    # wrapped with ElevenLabs' own status_code/message so the app-wide
    # handler can surface the real cause instead of a generic 500.
    _mock_settings(mocker)
    original = ApiError(
        status_code=402,
        body={
            "detail": {
                "type": "payment_required",
                "code": "paid_plan_required",
                "message": (
                    "Free users cannot use library voices via the API. "
                    "Please upgrade your subscription to use this voice."
                ),
                "status": "payment_required",
            }
        },
    )

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(ElevenLabsRequestError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value.status_code == 402
    assert "Free users cannot use library voices" in str(exc_info.value)
    assert exc_info.value.__cause__ is original


async def test_synthesize_speech_falls_back_to_str_when_body_has_no_detail_message(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    original = ApiError(status_code=400, body="not a dict")

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(ElevenLabsRequestError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value.status_code == 400


async def test_synthesize_speech_falls_back_to_str_when_detail_has_no_message_key(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    original = ApiError(status_code=400, body={"detail": {"code": "no_message_here"}})

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(ElevenLabsRequestError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value.status_code == 400


async def test_synthesize_speech_does_not_wrap_a_non_api_non_http_error(
    mocker: MockerFixture,
) -> None:
    # Something unrelated to ElevenLabs' own error shapes (e.g. a bug in
    # the SDK itself) must propagate unchanged, not get misreported as
    # either transient or a request-shaped ElevenLabs rejection.
    _mock_settings(mocker)
    original = RuntimeError("unexpected bug")

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(RuntimeError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value is original


async def test_synthesize_speech_defaults_status_code_when_api_error_has_none(
    mocker: MockerFixture,
) -> None:
    _mock_settings(mocker)
    original = ApiError(status_code=None, body="unknown")

    async def fake_convert(voice_id, **kwargs):
        raise original
        yield  # pragma: no cover

    fake_client = mocker.MagicMock()
    fake_client.text_to_speech.convert = fake_convert
    mocker.patch(
        "app.core.elevenlabs_client.get_elevenlabs_client", return_value=fake_client
    )

    with pytest.raises(ElevenLabsRequestError) as exc_info:
        await synthesize_speech(text="hello")

    assert exc_info.value.status_code == 422
