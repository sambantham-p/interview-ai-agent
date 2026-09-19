import io
import wave

from app.constants.voice import (
    GEMINI_TTS_CHANNELS,
    GEMINI_TTS_SAMPLE_RATE_HZ,
    GEMINI_TTS_SAMPLE_WIDTH_BYTES,
)


def pcm_to_wav(pcm_bytes: bytes) -> bytes:
    """Wrap raw 16-bit mono PCM (Gemini TTS's native output) in a WAV
    container so a browser can play it.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(GEMINI_TTS_CHANNELS)
        wav_file.setsampwidth(GEMINI_TTS_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(GEMINI_TTS_SAMPLE_RATE_HZ)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()
