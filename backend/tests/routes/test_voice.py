from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.elevenlabs_client import ElevenLabsRequestError, ElevenLabsTransientError
from app.core.llm_gateway import SpeechAudio
from app.core.session_lookup import InterviewSessionNotFoundError


def test_text_to_speech_returns_audio_bytes_on_success(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.voice.synthesize_speech_with_fallback",
        new_callable=mocker.AsyncMock,
        return_value=SpeechAudio(audio=b"fake-mp3-bytes", media_type="audio/mpeg"),
    )

    response = authed_client.post(
        "/api/v1/voice/tts", json={"text": "Hello, candidate."}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake-mp3-bytes"


def test_text_to_speech_passes_text_and_session_id_through(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    fake_synthesize = mocker.patch(
        "app.routes.voice.synthesize_speech_with_fallback",
        new_callable=mocker.AsyncMock,
        return_value=SpeechAudio(audio=b"audio", media_type="audio/mpeg"),
    )

    authed_client.post(
        "/api/v1/voice/tts", json={"text": "Take a moment, no rush.", "session_id": 7}
    )

    call_kwargs = fake_synthesize.call_args.kwargs
    assert call_kwargs["text"] == "Take a moment, no rush."
    assert call_kwargs["session_id"] == 7


def test_text_to_speech_rejects_blank_text(authed_client: TestClient) -> None:
    response = authed_client.post("/api/v1/voice/tts", json={"text": ""})

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_text_to_speech_returns_503_for_a_transient_elevenlabs_failure(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.voice.synthesize_speech_with_fallback",
        side_effect=ElevenLabsTransientError("elevenlabs down"),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post("/api/v1/voice/tts", json={"text": "Hello"})

    assert response.status_code == 503
    assert response.json()["success"] is False


def test_text_to_speech_returns_404_for_nonexistent_session_id(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.voice.synthesize_speech_with_fallback",
        side_effect=InterviewSessionNotFoundError("No interview session with id 99999"),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post(
        "/api/v1/voice/tts", json={"text": "Hello", "session_id": 99999}
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "99999" in body["error"]["message"]


def test_text_to_speech_returns_elevenlabs_own_status_and_message_for_a_request_error(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    # Not transient - ElevenLabs rejected this specific request (e.g. a
    # plan-restricted voice). Must surface as ElevenLabs' own status_code
    # and message, not a generic 500.
    mocker.patch(
        "app.routes.voice.synthesize_speech_with_fallback",
        side_effect=ElevenLabsRequestError(
            "Free users cannot use library voices via the API. Please "
            "upgrade your subscription to use this voice.",
            status_code=402,
        ),
        new_callable=mocker.AsyncMock,
    )

    response = authed_client.post("/api/v1/voice/tts", json={"text": "Hello"})

    assert response.status_code == 402
    body = response.json()
    assert body["success"] is False
    assert "Free users cannot use library voices" in body["error"]["message"]
