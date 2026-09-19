import { useState } from 'react'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { MicIcon, SendIcon, StopIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'
import { formatClock } from './usePhaseClock'
import { useVoiceRecorder } from './useVoiceRecorder'

const RECORDING_WARNING_SECONDS = 30

interface ComposerProps {
  sessionId: number
  maxAnswerSeconds: number
  isSending: boolean
  onSend: (message: string) => void
  onMicStart: () => void
}

export function Composer({ sessionId, maxAnswerSeconds, isSending, onSend, onMicStart }: ComposerProps) {
  const [draft, setDraft] = useState('')
  const recorder = useVoiceRecorder({
    sessionId,
    maxSeconds: maxAnswerSeconds,
    onRecordingStart: onMicStart,
    onTranscript: (text) => setDraft((current) => (current ? `${current} ${text}` : text)),
  })

  const isRecording = recorder.state === 'recording'
  const isTranscribing = recorder.state === 'transcribing'
  const secondsLeft = maxAnswerSeconds - recorder.elapsedSeconds
  const isNearLimit = isRecording && secondsLeft <= RECORDING_WARNING_SECONDS
  const canSend = draft.trim().length > 0 && !isSending && !isRecording && !isTranscribing

  function send() {
    if (!canSend) return
    onSend(draft.trim())
    setDraft('')
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <div className="space-y-2">
      <ErrorAlert message={recorder.error} />

      <div className="flex items-end gap-2 rounded-2xl border border-white/10 bg-white/6 p-2">
        {isRecording ? (
          <p className="flex-1 flex items-center gap-2.5 px-3 py-3 text-sm text-slate-200" role="status">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
            </span>
            Listening… {formatClock(recorder.elapsedSeconds)} / {formatClock(maxAnswerSeconds)}
            {isNearLimit && (
              <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-[11px] font-semibold text-amber-200">
                {secondsLeft}s left
              </span>
            )}
          </p>
        ) : (
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={isTranscribing}
            placeholder={isTranscribing ? 'Transcribing your answer…' : 'Type your answer, or tap the mic to speak'}
            aria-label="Your answer"
            className="flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] text-white placeholder:text-slate-500 focus:outline-none disabled:opacity-60"
          />
        )}

        <button
          type="button"
          onClick={isRecording ? recorder.stop : recorder.start}
          disabled={isTranscribing || isSending}
          aria-label={isRecording ? 'Stop recording' : 'Answer by voice'}
          className={`h-11 w-11 shrink-0 rounded-xl flex items-center justify-center transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
            isRecording ? 'bg-red-500 text-white hover:bg-red-600' : 'bg-white/10 text-slate-200 hover:bg-white/20'
          }`}
        >
          {isTranscribing ? <Spinner /> : isRecording ? <StopIcon className="w-5 h-5" /> : <MicIcon className="w-5 h-5" />}
        </button>

        <button
          type="button"
          onClick={send}
          disabled={!canSend}
          aria-label="Send answer"
          className="h-11 w-11 shrink-0 rounded-xl bg-brand text-[#06251f] flex items-center justify-center transition-colors hover:bg-[#14c3a8] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isSending ? <Spinner /> : <SendIcon className="w-5 h-5" />}
        </button>
      </div>
      <p className="px-1 text-[11px] text-slate-500">
        Enter to send · Shift+Enter for a new line · a spoken answer lands here first so you can edit it
      </p>
    </div>
  )
}
