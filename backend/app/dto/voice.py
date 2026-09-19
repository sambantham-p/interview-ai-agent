from pydantic import BaseModel, Field

from app.constants.voice import MAX_TTS_TEXT_LENGTH


class TextToSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_TEXT_LENGTH)
    session_id: int | None = Field(
        default=None,
        description=(
            "Interview session this call is billed against, for the "
            "per-interview voice cost cap. Omit for a standalone call "
            "not tied to a live interview."
        ),
    )
