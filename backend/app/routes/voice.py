from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.voice import TTS_AUDIO_MEDIA_TYPE
from app.core.db import get_db
from app.core.llm_gateway import synthesize_speech
from app.schemas.voice import TextToSpeechRequest

router = APIRouter(tags=["Voice"])


@router.post("/voice/tts")
async def text_to_speech(
    payload: TextToSpeechRequest, db: AsyncSession = Depends(get_db)
) -> Response:
    """Synthesize speech for the Interviewer's reply text via ElevenLabs.

    Returns the generated MP3 audio as raw bytes.
    """
    audio_bytes = await synthesize_speech(
        text=payload.text, session_id=payload.session_id, db=db
    )
    return Response(content=audio_bytes, media_type=TTS_AUDIO_MEDIA_TYPE)
