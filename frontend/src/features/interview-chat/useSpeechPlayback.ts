import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'


export const TTS_LOAD_TIMEOUT_MS = 10_000


export function useSpeechPlayback(sessionId: number) {
  const [playingKey, setPlayingKey] = useState<number | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const objectUrlRef = useRef<string | null>(null)
  const requestRef = useRef(0)

  const stop = useCallback(() => {
    requestRef.current += 1
    audioRef.current?.pause()
    audioRef.current = null
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    objectUrlRef.current = null
    setPlayingKey(null)
  }, [])

  // The spoken audio for `text`, or null when no voice could be produced
  // in time.
  const load = useCallback(
    async (text: string): Promise<Blob | null> => {
      try {
        return await api.postForBlob(
          '/voice/tts',
          { text, session_id: sessionId },
          AbortSignal.timeout(TTS_LOAD_TIMEOUT_MS),
        )
      } catch {
        return null
      }
    },
    [sessionId],
  )

  // `key` identifies the message being spoken (its transcript index).
  const play = useCallback(
    (key: number, audioBlob: Blob) => {
      stop()
      const url = URL.createObjectURL(audioBlob)
      const audio = new Audio(url)
      objectUrlRef.current = url
      audioRef.current = audio
      audio.onended = stop
      setPlayingKey(key)
      audio.play().catch(stop)
    },
    [stop],
  )

  // Loads and plays a message on demand (the replay button).
  const speak = useCallback(
    async (key: number, text: string) => {
      stop()
      const requestId = requestRef.current
      setPlayingKey(key)
      const audioBlob = await load(text)
      if (requestId !== requestRef.current) return
      if (audioBlob) play(key, audioBlob)
      else stop()
    },
    [load, play, stop],
  )

  useEffect(() => stop, [stop])

  return { playingKey, load, play, speak, stop }
}
