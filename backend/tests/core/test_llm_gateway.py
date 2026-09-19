import pytest
from google.genai import types
from pydantic import BaseModel
from pytest_mock import MockerFixture

from app.core.config import ElevenLabsSettings, GatewaySettings
from app.core.elevenlabs_client import ElevenLabsRequestError, ElevenLabsTransientError
from app.core.llm_gateway import (
    SpeechAudio,
    generate_structured,
    generate_structured_with_tools,
    stream_text,
    synthesize_speech,
)
from app.core.session_lookup import InterviewSessionNotFoundError


class _FakeOutput(BaseModel):
    value: str


def _mock_gateway_settings(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.llm_gateway.get_gateway_settings",
        return_value=GatewaySettings(
            gemini_interviewer_model="gemini-3.8-flash",
            gemini_judge_model="gemini-3.1-pro",
            gemini_stt_model="gemini-stt",
            gemini_tts_model="gemini-tts",
        ),
    )


def _mock_log_session(mocker: MockerFixture):
    """_log_call() logs on its own DB session (see llm_gateway.py) rather
    than the caller's `db` - patch app.core.llm_gateway.get_session_factory
    to intercept what actually gets logged, instead of asserting on the
    caller's `db` mock.
    """
    fake_log_db = mocker.AsyncMock()
    fake_log_db.add = mocker.MagicMock()
    fake_log_db.__aenter__ = mocker.AsyncMock(return_value=fake_log_db)
    fake_log_db.__aexit__ = mocker.AsyncMock(return_value=False)
    mocker.patch(
        "app.core.llm_gateway.get_session_factory",
        return_value=lambda: fake_log_db,
    )
    return fake_log_db


async def test_generate_structured_resolves_model_and_logs_success(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=10, candidates_token_count=5, total_token_count=15
    )

    async def fake_extract_structured(**kwargs):
        kwargs["on_usage"](usage)
        return _FakeOutput(value="hi")

    mocker.patch(
        "app.core.llm_gateway.extract_structured", side_effect=fake_extract_structured
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    result = await generate_structured(
        task="interviewer",
        contents=[types.Part.from_text(text="hello")],
        text_format=_FakeOutput,
        system_instruction="system",
        thinking_level="high",
        session_id=42,
        db=fake_db,
    )

    assert result == _FakeOutput(value="hi")
    fake_log_db.add.assert_called_once()
    logged = fake_log_db.add.call_args.args[0]
    assert logged.task == "interviewer"
    assert logged.model == "gemini-3.8-flash"
    assert logged.session_id == 42
    assert logged.prompt_token_count == 10
    assert logged.error is None
    fake_log_db.commit.assert_awaited_once()
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_awaited()


async def test_generate_structured_logs_error_and_reraises(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)

    async def fake_extract_structured(**kwargs):
        kwargs["on_usage"](None)
        raise ValueError("boom")

    mocker.patch(
        "app.core.llm_gateway.extract_structured", side_effect=fake_extract_structured
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    try:
        await generate_structured(
            task="interviewer",
            contents=[types.Part.from_text(text="hello")],
            text_format=_FakeOutput,
            system_instruction="system",
            thinking_level="high",
            session_id=None,
            db=fake_db,
        )
        raise AssertionError("expected ValueError to propagate")
    except ValueError:
        pass

    logged = fake_log_db.add.call_args.args[0]
    assert logged.error == "boom"
    assert logged.response == ""
    # A failed call must still log (above) without ever touching the
    # caller's own db/transaction - e.g. start_interview flushes a
    # not-yet-fully-populated InterviewSession before this call; logging
    # must never be what durably commits it.
    fake_db.add.assert_not_called()
    fake_db.commit.assert_not_awaited()


async def test_generate_structured_accepts_multi_turn_content_history(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)
    captured_contents = {}

    async def fake_extract_structured(**kwargs):
        captured_contents["contents"] = kwargs["contents"]
        kwargs["on_usage"](None)
        return _FakeOutput(value="ok")

    mocker.patch(
        "app.core.llm_gateway.extract_structured", side_effect=fake_extract_structured
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()
    history = [
        types.Content(role="user", parts=[types.Part.from_text(text="question one")]),
        types.Content(role="model", parts=[types.Part.from_text(text="answer one")]),
    ]

    await generate_structured(
        task="interviewer",
        contents=history,
        text_format=_FakeOutput,
        system_instruction="system",
        thinking_level="medium",
        session_id=1,
        db=fake_db,
    )

    assert captured_contents["contents"] == history
    logged = fake_log_db.add.call_args.args[0]
    assert "question one" in logged.prompt
    assert "answer one" in logged.prompt


async def test_stream_text_yields_chunks_and_logs_accumulated_response(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)

    async def _fake_stream():
        chunk1 = mocker.MagicMock(text="Hello ", usage_metadata=None)
        chunk2 = mocker.MagicMock(
            text="world",
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                total_token_count=3
            ),
        )
        for chunk in (chunk1, chunk2):
            yield chunk

    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_fake_stream()
    )
    mocker.patch("app.core.llm_gateway.get_gemini_client", return_value=fake_client)
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    chunks = [
        chunk
        async for chunk in stream_text(
            task="interviewer",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="system",
            thinking_level="low",
            session_id=7,
            db=fake_db,
        )
    ]

    assert chunks == ["Hello ", "world"]
    logged = fake_log_db.add.call_args.args[0]
    assert logged.response == "Hello world"
    assert logged.total_token_count == 3
    assert logged.error is None


async def test_stream_text_logs_error_when_stream_raises(mocker: MockerFixture) -> None:
    _mock_gateway_settings(mocker)
    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content_stream = mocker.AsyncMock(
        side_effect=RuntimeError("stream blew up")
    )
    mocker.patch("app.core.llm_gateway.get_gemini_client", return_value=fake_client)
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    try:
        async for _ in stream_text(
            task="interviewer",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="system",
            thinking_level="low",
            session_id=None,
            db=fake_db,
        ):
            pass
        raise AssertionError("expected RuntimeError to propagate")
    except RuntimeError:
        pass

    logged = fake_log_db.add.call_args.args[0]
    assert logged.error == "stream blew up"


def _mock_elevenlabs_settings(mocker: MockerFixture) -> None:
    mocker.patch(
        "app.core.llm_gateway.get_elevenlabs_settings",
        return_value=ElevenLabsSettings(
            elevenlabs_api_key="test-key",
            elevenlabs_voice_id="voice-1",
            elevenlabs_model_id="eleven_multilingual_v2",
        ),
    )


async def test_synthesize_speech_returns_audio_and_logs_character_count(
    mocker: MockerFixture,
) -> None:
    _mock_elevenlabs_settings(mocker)
    mocker.patch(
        "app.core.llm_gateway._synthesize_speech",
        new_callable=mocker.AsyncMock,
        return_value=b"fake-audio-bytes",
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()
    fake_db.get.return_value = mocker.MagicMock(user_id="usr_test123")

    result = await synthesize_speech(
        text="hello there", session_id=5, user_id="usr_test123", db=fake_db
    )

    assert result == b"fake-audio-bytes"
    logged = fake_log_db.add.call_args.args[0]
    assert logged.task == "tts"
    assert logged.model == "eleven_multilingual_v2"
    assert logged.session_id == 5
    assert logged.prompt == "hello there"
    assert logged.extra == {"character_count": len("hello there")}
    assert logged.error is None
    fake_log_db.commit.assert_awaited_once()


async def test_synthesize_speech_raises_for_nonexistent_session_without_calling_elevenlabs(
    mocker: MockerFixture,
) -> None:
    _mock_elevenlabs_settings(mocker)
    fake_elevenlabs = mocker.patch(
        "app.core.llm_gateway._synthesize_speech",
        new_callable=mocker.AsyncMock,
    )
    fake_db = mocker.AsyncMock()
    fake_db.get = mocker.AsyncMock(return_value=None)

    try:
        await synthesize_speech(
            text="hello", session_id=99999, user_id="usr_test123", db=fake_db
        )
        raise AssertionError("expected InterviewSessionNotFoundError to propagate")
    except InterviewSessionNotFoundError:
        pass

    fake_elevenlabs.assert_not_called()
    fake_db.add.assert_not_called()


async def test_synthesize_speech_logs_error_and_reraises(
    mocker: MockerFixture,
) -> None:
    _mock_elevenlabs_settings(mocker)
    mocker.patch(
        "app.core.llm_gateway._synthesize_speech",
        new_callable=mocker.AsyncMock,
        side_effect=RuntimeError("elevenlabs down"),
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    try:
        await synthesize_speech(text="hello", session_id=None, user_id=None, db=fake_db)
        raise AssertionError("expected RuntimeError to propagate")
    except RuntimeError:
        pass

    logged = fake_log_db.add.call_args.args[0]
    assert logged.error == "elevenlabs down"
    assert logged.response == ""
    assert logged.extra == {"character_count": len("hello")}


async def test_generate_structured_with_tools_runs_tool_loop_then_final_structured_call(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)
    history_after_tools = [
        types.Content(role="user", parts=[types.Part.from_text(text="hi")])
    ]
    fake_run_tool_loop = mocker.patch(
        "app.core.llm_gateway.run_tool_loop",
        new_callable=mocker.AsyncMock,
        return_value=history_after_tools,
    )
    fake_generate_structured = mocker.patch(
        "app.core.llm_gateway.generate_structured",
        new_callable=mocker.AsyncMock,
        return_value=_FakeOutput(value="final"),
    )
    fake_db = mocker.AsyncMock()

    result = await generate_structured_with_tools(
        task="interviewer",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        text_format=_FakeOutput,
        system_instruction="system",
        thinking_level="medium",
        tools=[],
        tool_dispatch={},
        max_rounds=4,
        session_id=7,
        db=fake_db,
    )

    assert result == _FakeOutput(value="final")
    fake_run_tool_loop.assert_awaited_once()
    tool_loop_kwargs = fake_run_tool_loop.call_args.kwargs
    assert tool_loop_kwargs["model"] == "gemini-3.8-flash"
    assert tool_loop_kwargs["max_rounds"] == 4
    assert callable(tool_loop_kwargs["on_round"])

    fake_generate_structured.assert_awaited_once()
    final_kwargs = fake_generate_structured.call_args.kwargs
    assert final_kwargs["task"] == "interviewer"
    assert final_kwargs["contents"] == history_after_tools
    assert final_kwargs["session_id"] == 7


async def test_generate_structured_with_tools_logs_each_tool_round(
    mocker: MockerFixture,
) -> None:
    _mock_gateway_settings(mocker)
    usage = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=3, candidates_token_count=2, total_token_count=5
    )

    async def fake_run_tool_loop(**kwargs):
        fake_response = mocker.MagicMock()
        fake_response.text = None
        fake_response.usage_metadata = usage
        await kwargs["on_round"](0, fake_response, 0.5)
        return [types.Content(role="user", parts=[types.Part.from_text(text="hi")])]

    mocker.patch("app.core.llm_gateway.run_tool_loop", side_effect=fake_run_tool_loop)
    mocker.patch(
        "app.core.llm_gateway.generate_structured",
        new_callable=mocker.AsyncMock,
        return_value=_FakeOutput(value="final"),
    )
    fake_log_db = _mock_log_session(mocker)
    fake_db = mocker.AsyncMock()

    await generate_structured_with_tools(
        task="interviewer",
        contents=[types.Content(role="user", parts=[types.Part.from_text(text="hi")])],
        text_format=_FakeOutput,
        system_instruction="system",
        thinking_level="medium",
        tools=[],
        tool_dispatch={},
        max_rounds=4,
        session_id=7,
        db=fake_db,
    )

    fake_log_db.add.assert_called_once()
    logged = fake_log_db.add.call_args.args[0]
    assert logged.task == "interviewer_tool_call"
    assert logged.model == "gemini-3.8-flash"
    assert logged.session_id == 7
    assert logged.response == "<function call>"
    assert logged.prompt_token_count == 3
    assert logged.latency_seconds == 0.5


def test_gateway_settings_model_for_task_resolves_interviewer() -> None:
    settings = GatewaySettings(
        gemini_interviewer_model="gemini-3.8-flash",
        gemini_judge_model="gemini-3.1-pro",
        gemini_stt_model="gemini-stt",
        gemini_tts_model="gemini-tts",
    )

    assert settings.model_for_task("interviewer") == "gemini-3.8-flash"


def test_gateway_settings_model_for_task_raises_for_unknown_task() -> None:
    settings = GatewaySettings(
        gemini_interviewer_model="gemini-3.8-flash",
        gemini_judge_model="gemini-3.1-pro",
        gemini_stt_model="gemini-stt",
        gemini_tts_model="gemini-tts",
    )

    try:
        settings.model_for_task("unknown_task")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_truncate_caps_long_text_and_leaves_short_text_alone() -> None:
    from app.core.llm_gateway import _MAX_LOGGED_CHARS, _truncate

    assert _truncate("short") == "short"
    truncated = _truncate("x" * (_MAX_LOGGED_CHARS + 10))
    assert truncated.endswith("...[truncated]")
    assert len(truncated) == _MAX_LOGGED_CHARS + len("...[truncated]")


async def test_log_call_swallows_database_failures(mocker: MockerFixture) -> None:
    from app.core.llm_gateway import _log_call

    fake_log_db = _mock_log_session(mocker)
    fake_log_db.commit = mocker.AsyncMock(side_effect=RuntimeError("db down"))

    await _log_call(
        task="t",
        model="m",
        session_id=None,
        prompt="p",
        response="r",
        latency_seconds=0.1,
        usage=None,
        error=None,
    )


def test_usage_recorder_remembers_the_last_usage() -> None:
    from app.core.llm_gateway import _UsageRecorder

    recorder = _UsageRecorder()
    assert recorder.usage is None
    recorder("usage")
    assert recorder.usage == "usage"


async def test_transcribe_speech_returns_text_and_logs_audio_size(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import transcribe_speech

    _mock_gateway_settings(mocker)
    fake_log_db = _mock_log_session(mocker)
    fake_transcribe = mocker.patch(
        "app.core.llm_gateway.transcribe_audio",
        new_callable=mocker.AsyncMock,
        return_value="hello world",
    )

    text = await transcribe_speech(
        audio_bytes=b"12345",
        mime_type="audio/webm",
        session_id=None,
        user_id=None,
        db=mocker.AsyncMock(),
        vocabulary=["Python"],
    )

    assert text == "hello world"
    assert fake_transcribe.call_args.kwargs["model"] == "gemini-stt"
    assert fake_transcribe.call_args.kwargs["vocabulary"] == ["Python"]
    logged = fake_log_db.add.call_args.args[0]
    assert logged.task == "stt"
    assert logged.extra == {"audio_bytes": 5, "mime_type": "audio/webm"}
    assert logged.error is None


async def test_transcribe_speech_logs_error_and_reraises(mocker: MockerFixture) -> None:
    from app.core.llm_gateway import transcribe_speech

    _mock_gateway_settings(mocker)
    fake_log_db = _mock_log_session(mocker)
    mocker.patch(
        "app.core.llm_gateway.transcribe_audio",
        new_callable=mocker.AsyncMock,
        side_effect=RuntimeError("stt down"),
    )

    with pytest.raises(RuntimeError, match="stt down"):
        await transcribe_speech(
            audio_bytes=b"1",
            mime_type="audio/webm",
            session_id=None,
            user_id=None,
            db=mocker.AsyncMock(),
        )

    assert fake_log_db.add.call_args.args[0].error == "stt down"


async def test_synthesize_speech_gemini_wraps_pcm_as_wav_and_logs(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import _synthesize_speech_gemini

    _mock_gateway_settings(mocker)
    fake_log_db = _mock_log_session(mocker)
    mocker.patch(
        "app.core.llm_gateway.generate_speech",
        new_callable=mocker.AsyncMock,
        return_value=b"\x00\x00" * 10,
    )

    speech = await _synthesize_speech_gemini(text="Hello", session_id=None)

    assert speech.media_type == "audio/wav"
    assert speech.audio.startswith(b"RIFF")
    assert fake_log_db.add.call_args.args[0].task == "tts_gemini"


async def test_synthesize_speech_gemini_logs_error_and_reraises(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import _synthesize_speech_gemini

    _mock_gateway_settings(mocker)
    fake_log_db = _mock_log_session(mocker)
    mocker.patch(
        "app.core.llm_gateway.generate_speech",
        new_callable=mocker.AsyncMock,
        side_effect=RuntimeError("tts down"),
    )

    with pytest.raises(RuntimeError, match="tts down"):
        await _synthesize_speech_gemini(text="Hello", session_id=None)

    assert fake_log_db.add.call_args.args[0].error == "tts down"


async def test_voice_task_in_use_returns_the_latest_successful_task(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import _voice_task_in_use

    db = mocker.AsyncMock()
    db.execute.return_value = mocker.MagicMock(
        scalar_one_or_none=mocker.MagicMock(return_value="tts")
    )

    assert await _voice_task_in_use(5, db) == "tts"


def _patch_fallback_dependencies(mocker: MockerFixture, voice_in_use: str | None):
    mocker.patch(
        "app.core.llm_gateway._authorize_session", new_callable=mocker.AsyncMock
    )
    mocker.patch(
        "app.core.llm_gateway._voice_task_in_use",
        new_callable=mocker.AsyncMock,
        return_value=voice_in_use,
    )
    gemini = mocker.patch(
        "app.core.llm_gateway._synthesize_speech_gemini",
        new_callable=mocker.AsyncMock,
        return_value=SpeechAudio(audio=b"wav", media_type="audio/wav"),
    )
    eleven = mocker.patch(
        "app.core.llm_gateway.synthesize_speech", new_callable=mocker.AsyncMock
    )
    return gemini, eleven


async def test_fallback_uses_elevenlabs_when_available(mocker: MockerFixture) -> None:
    from app.core.llm_gateway import synthesize_speech_with_fallback

    gemini, eleven = _patch_fallback_dependencies(mocker, None)
    eleven.return_value = b"mp3"

    speech = await synthesize_speech_with_fallback(
        text="Hi", session_id=3, user_id="u", db=mocker.AsyncMock()
    )

    assert speech == SpeechAudio(audio=b"mp3", media_type="audio/mpeg")
    gemini.assert_not_called()


async def test_fallback_stays_on_gemini_once_the_session_uses_it(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import synthesize_speech_with_fallback

    gemini, eleven = _patch_fallback_dependencies(mocker, "tts_gemini")

    speech = await synthesize_speech_with_fallback(
        text="Hi", session_id=3, user_id="u", db=mocker.AsyncMock()
    )

    assert speech.media_type == "audio/wav"
    eleven.assert_not_called()
    gemini.assert_awaited_once()


async def test_fallback_switches_to_gemini_before_any_audio_was_produced(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import synthesize_speech_with_fallback

    gemini, eleven = _patch_fallback_dependencies(mocker, None)
    eleven.side_effect = ElevenLabsTransientError("down")

    speech = await synthesize_speech_with_fallback(
        text="Hi", session_id=None, user_id=None, db=mocker.AsyncMock()
    )

    assert speech.media_type == "audio/wav"
    gemini.assert_awaited_once()


async def test_fallback_never_switches_voice_mid_interview(
    mocker: MockerFixture,
) -> None:
    from app.core.llm_gateway import synthesize_speech_with_fallback

    gemini, eleven = _patch_fallback_dependencies(mocker, "tts")
    eleven.side_effect = ElevenLabsRequestError("bad request", status_code=400)

    with pytest.raises(ElevenLabsRequestError):
        await synthesize_speech_with_fallback(
            text="Hi", session_id=3, user_id="u", db=mocker.AsyncMock()
        )

    gemini.assert_not_called()


async def test_stream_text_skips_chunks_without_text(mocker: MockerFixture) -> None:
    _mock_gateway_settings(mocker)

    async def _fake_stream():
        yield mocker.MagicMock(text="", usage_metadata=None)
        yield mocker.MagicMock(text="Hi", usage_metadata=None)

    fake_client = mocker.MagicMock()
    fake_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_fake_stream()
    )
    mocker.patch("app.core.llm_gateway.get_gemini_client", return_value=fake_client)
    _mock_log_session(mocker)

    chunks = [
        chunk
        async for chunk in stream_text(
            task="interviewer",
            contents=[
                types.Content(role="user", parts=[types.Part.from_text(text="hi")])
            ],
            system_instruction="system",
            thinking_level="low",
            session_id=None,
            db=mocker.AsyncMock(),
        )
    ]

    assert chunks == ["Hi"]
