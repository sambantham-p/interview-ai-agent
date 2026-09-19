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


def _post_audio(
    client: TestClient,
    content: bytes = b"audio-bytes",
    content_type: str = "audio/webm;codecs=opus",
    data: dict | None = None,
):
    return client.post(
        "/api/v1/voice/stt",
        files={"audio": ("answer.webm", content, content_type)},
        data=data or {},
    )


def test_speech_to_text_returns_the_transcript(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    fake_transcribe = mocker.patch(
        "app.routes.voice.transcribe_speech",
        new_callable=mocker.AsyncMock,
        return_value="I used a hash map.",
    )

    response = _post_audio(authed_client)

    assert response.status_code == 200
    assert response.json()["data"]["text"] == "I used a hash map."
    call_kwargs = fake_transcribe.call_args.kwargs
    assert call_kwargs["mime_type"] == "audio/webm"
    assert call_kwargs["vocabulary"] is None


def test_speech_to_text_passes_the_jd_tech_stack_as_vocabulary(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    job = mocker.Mock(tech_stack=["Python", "FastAPI"])
    mocker.patch(
        "app.routes.voice.get_interview_with_job",
        new_callable=mocker.AsyncMock,
        return_value=(mocker.Mock(), job),
    )
    fake_transcribe = mocker.patch(
        "app.routes.voice.transcribe_speech",
        new_callable=mocker.AsyncMock,
        return_value="text",
    )

    response = _post_audio(authed_client, data={"session_id": "5"})

    assert response.status_code == 200
    assert fake_transcribe.call_args.kwargs["vocabulary"] == ["Python", "FastAPI"]
    assert fake_transcribe.call_args.kwargs["session_id"] == 5


def test_speech_to_text_rejects_a_non_audio_upload(authed_client: TestClient) -> None:
    response = _post_audio(authed_client, content_type="text/plain")

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Upload an audio recording."


def test_speech_to_text_rejects_an_empty_recording(authed_client: TestClient) -> None:
    response = _post_audio(authed_client, content=b"")

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "The recording was empty."


def test_speech_to_text_rejects_an_oversized_recording(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch("app.routes.voice.MAX_STT_AUDIO_BYTES", 4)

    response = _post_audio(authed_client, content=b"12345")

    assert response.status_code == 413


def test_speech_to_text_returns_404_for_an_unknown_session(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.voice.get_interview_with_job",
        side_effect=InterviewSessionNotFoundError("No interview session with id 9"),
        new_callable=mocker.AsyncMock,
    )

    response = _post_audio(authed_client, data={"session_id": "9"})

    assert response.status_code == 404


def test_speech_to_text_returns_422_when_nothing_was_heard(
    authed_client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        "app.routes.voice.transcribe_speech",
        new_callable=mocker.AsyncMock,
        return_value="",
    )

    response = _post_audio(authed_client)

    assert response.status_code == 422
    assert "Couldn't hear anything" in response.json()["error"]["message"]
