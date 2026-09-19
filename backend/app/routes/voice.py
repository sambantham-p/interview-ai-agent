from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.voice import MAX_STT_AUDIO_BYTES
from app.core.db import get_db
from app.core.llm_gateway import synthesize_speech_with_fallback, transcribe_speech
from app.core.responses import error_response, success_response
from app.core.session_lookup import InterviewSessionNotFoundError
from app.dto.voice import SpeechToTextResponse, TextToSpeechRequest
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.interview_service import get_interview_with_job

router = APIRouter(tags=["Voice"])

AUDIO_MIME_PREFIX = "audio/"
# MediaRecorder reports types like "audio/webm;codecs=opus"; Gemini wants
# just the base type.
MIME_PARAMETER_SEPARATOR = ";"


@router.post("/voice/tts")
async def text_to_speech(
    payload: TextToSpeechRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Synthesize speech for the Interviewer's reply text.

    Uses ElevenLabs, falling back to Gemini TTS when ElevenLabs is
    unavailable. Returns the audio as raw bytes (MP3 or WAV, per the
    response's content type).
    """
    try:
        speech = await synthesize_speech_with_fallback(
            text=payload.text, session_id=payload.session_id, user_id=user.id, db=db
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    return Response(content=speech.audio, media_type=speech.media_type)


@router.post("/voice/stt", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio: UploadFile,
    session_id: Annotated[int | None, Form()] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Transcribe a recorded answer to text with Gemini, so the candidate
    can review and edit it before sending it as a turn.
    """
    mime_type = (audio.content_type or "").split(MIME_PARAMETER_SEPARATOR)[0].strip()
    if not mime_type.startswith(AUDIO_MIME_PREFIX):
        return error_response(
            message="Upload an audio recording.",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )

    audio_bytes = await audio.read(MAX_STT_AUDIO_BYTES + 1)
    if not audio_bytes:
        return error_response(
            message="The recording was empty.",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )
    if len(audio_bytes) > MAX_STT_AUDIO_BYTES:
        return error_response(
            message="The recording is too long. Try a shorter answer.",
            status_code=httpx.codes.REQUEST_ENTITY_TOO_LARGE,
        )

    try:
        vocabulary = None
        if session_id is not None:
            _, job_description = await get_interview_with_job(
                session_id=session_id, user_id=user.id, db=db
            )
            vocabulary = job_description.tech_stack
        text = await transcribe_speech(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            session_id=session_id,
            user_id=user.id,
            db=db,
            vocabulary=vocabulary,
        )
    except InterviewSessionNotFoundError as exc:
        return error_response(message=str(exc), status_code=httpx.codes.NOT_FOUND)

    if not text:
        return error_response(
            message="Couldn't hear anything in that recording. Try again or type your answer.",
            status_code=httpx.codes.UNPROCESSABLE_ENTITY,
        )
    return success_response(
        data=SpeechToTextResponse(text=text), status_code=httpx.codes.OK
    )
