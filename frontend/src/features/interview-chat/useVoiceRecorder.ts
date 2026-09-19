import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import type { SpeechToTextResult } from '../../types/api'


const RECORDING_BITS_PER_SECOND = 32_000

const MIC_UNAVAILABLE_MESSAGE =
  'Microphone access is unavailable. You can type your answer instead.'

type RecorderState = 'idle' | 'recording' | 'transcribing'

interface UseVoiceRecorderOptions {
  sessionId: number
  maxSeconds: number
  onTranscript: (text: string) => void
  onRecordingStart?: () => void
}


export function useVoiceRecorder({
  sessionId,
  maxSeconds,
  onTranscript,
  onRecordingStart,
}: UseVoiceRecorderOptions) {
  const [isRecording, setIsRecording] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [micError, setMicError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const transcribe = useMutation({
    mutationFn: (recording: Blob) => {
      const formData = new FormData()
      formData.append('audio', recording, 'answer.webm')
      formData.append('session_id', String(sessionId))
      return api.upload<SpeechToTextResult>('/voice/stt', formData)
    },
    onSuccess: (result) => onTranscript(result.text),
  })

  const releaseMicrophone = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const stop = useCallback(() => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }, [])

  const start = useCallback(async () => {
    setMicError(null)
    transcribe.reset()
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setMicError(MIC_UNAVAILABLE_MESSAGE)
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setMicError(MIC_UNAVAILABLE_MESSAGE)
      return
    }

    const recorder = new MediaRecorder(stream, { audioBitsPerSecond: RECORDING_BITS_PER_SECOND })
    chunksRef.current = []
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }
    recorder.onstop = () => {
      releaseMicrophone()
      setIsRecording(false)
      const recording = new Blob(chunksRef.current, { type: recorder.mimeType })
      if (recording.size > 0) transcribe.mutate(recording)
    }

    streamRef.current = stream
    recorderRef.current = recorder
    recorder.start()
    setElapsedSeconds(0)
    setIsRecording(true)
    onRecordingStart?.()
  }, [onRecordingStart, releaseMicrophone, transcribe])

  useEffect(() => {
    if (!isRecording) return
    const timer = setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000)
    return () => clearInterval(timer)
  }, [isRecording])

  useEffect(() => {
    if (isRecording && elapsedSeconds >= maxSeconds) stop()
  }, [isRecording, elapsedSeconds, maxSeconds, stop])

  // Release the microphone if the page is left mid-recording.
  useEffect(
    () => () => {
      if (recorderRef.current?.state === 'recording') recorderRef.current.onstop = null
      recorderRef.current?.stop()
      releaseMicrophone()
    },
    [releaseMicrophone],
  )

  const state: RecorderState = isRecording
    ? 'recording'
    : transcribe.isPending
      ? 'transcribing'
      : 'idle'

  const error =
    micError ??
    (transcribe.error ? toErrorMessage(transcribe.error, 'Could not transcribe that recording.') : null)

  return { state, elapsedSeconds, error, start, stop }
}
