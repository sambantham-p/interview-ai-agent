from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.elevenlabs_client import ElevenLabsRequestError, ElevenLabsTransientError
from app.main import app


def test_text_to_speech_returns_audio_bytes_on_success(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.routes.voice.synthesize_speech",
        new_callable=mocker.AsyncMock,
        return_value=b"fake-mp3-bytes",
    )
    client = TestClient(app)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello, candidate."})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake-mp3-bytes"


def test_text_to_speech_passes_text_and_session_id_through(
    mocker: MockerFixture,
) -> None:
    fake_synthesize = mocker.patch(
        "app.routes.voice.synthesize_speech",
        new_callable=mocker.AsyncMock,
        return_value=b"audio",
    )
    client = TestClient(app)

    client.post(
        "/api/v1/voice/tts", json={"text": "Take a moment, no rush.", "session_id": 7}
    )

    call_kwargs = fake_synthesize.call_args.kwargs
    assert call_kwargs["text"] == "Take a moment, no rush."
    assert call_kwargs["session_id"] == 7


def test_text_to_speech_rejects_blank_text(client: TestClient) -> None:
    response = client.post("/api/v1/voice/tts", json={"text": ""})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_text_to_speech_returns_503_for_a_transient_elevenlabs_failure(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "app.routes.voice.synthesize_speech",
        side_effect=ElevenLabsTransientError("elevenlabs down"),
        new_callable=mocker.AsyncMock,
    )
    client = TestClient(app)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello"})

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_text_to_speech_returns_elevenlabs_own_status_and_message_for_a_request_error(
    mocker: MockerFixture,
) -> None:
    # Not transient - ElevenLabs rejected this specific request (e.g. a
    # plan-restricted voice). Must surface as ElevenLabs' own status_code
    # and message, not a generic 500.
    mocker.patch(
        "app.routes.voice.synthesize_speech",
        side_effect=ElevenLabsRequestError(
            "Free users cannot use library voices via the API. Please "
            "upgrade your subscription to use this voice.",
            status_code=402,
        ),
        new_callable=mocker.AsyncMock,
    )
    client = TestClient(app)

    response = client.post("/api/v1/voice/tts", json={"text": "Hello"})

    assert response.status_code == 402
    body = response.json()
    assert body["success"] is False
    assert "Free users cannot use library voices" in body["error"]["message"]
