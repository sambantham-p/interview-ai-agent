import io
import wave

from app.constants.voice import (
    GEMINI_TTS_CHANNELS,
    GEMINI_TTS_SAMPLE_RATE_HZ,
    GEMINI_TTS_SAMPLE_WIDTH_BYTES,
)
from app.utils.audio import pcm_to_wav


def test_pcm_to_wav_wraps_pcm_in_a_readable_wav_container() -> None:
    pcm = b"\x01\x00" * 100

    wav_bytes = pcm_to_wav(pcm)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == GEMINI_TTS_CHANNELS
        assert wav_file.getsampwidth() == GEMINI_TTS_SAMPLE_WIDTH_BYTES
        assert wav_file.getframerate() == GEMINI_TTS_SAMPLE_RATE_HZ
        assert wav_file.readframes(100) == pcm
