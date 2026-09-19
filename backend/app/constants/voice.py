ELEVENLABS_CLIENT_TIMEOUT_SECONDS = 30.0
ELEVENLABS_RATE_LIMIT_STATUS_CODE = 429
TTS_OUTPUT_FORMAT = "mp3_44100_128"
TTS_AUDIO_MEDIA_TYPE = "audio/mpeg"
MAX_TTS_TEXT_LENGTH = 5_000
TTS_TASK = "tts"
STT_TASK = "stt"
GEMINI_TTS_TASK = "tts_gemini"

# Largest raw audio recording accepted for transcription. Gemini allows up to
# 20 MB per inline request, while Base64 encoding increases the payload size
# by roughly one-third. This keeps the raw audio below the effective limit
# with sufficient headroom. At 128 kbps, an 8-minute recording is approximately
# 7.7 MB, which is below the raw audio limit.
MAX_STT_AUDIO_BYTES = 12 * 1024 * 1024
GEMINI_TTS_VOICE_NAME = "Kore"
GEMINI_TTS_SAMPLE_RATE_HZ = 24_000
GEMINI_TTS_SAMPLE_WIDTH_BYTES = 2
GEMINI_TTS_CHANNELS = 1
WAV_AUDIO_MEDIA_TYPE = "audio/wav"
