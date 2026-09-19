import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ErrorState } from '../../components/ui/ErrorState'
import { Spinner } from '../../components/ui/Spinner'
import { ApiRequestError, api } from '../../lib/api'
import { toErrorMessage } from '../../lib/errorMessage'
import { useGenerateReport, useInterview } from '../../lib/queries'
import { useOnlineStatus } from '../../lib/useOnlineStatus'
import type { InterviewDetail, InterviewTurn } from '../../types/api'
import { Composer } from './Composer'
import { EndedPanel } from './EndedPanel'
import { InterviewHeader } from './InterviewHeader'
import { appendTurn } from './interviewTranscript'
import { MessageBubble } from './MessageBubble'
import { useSpeechPlayback } from './useSpeechPlayback'

const NETWORK_ERROR_STATUS = 0

function Banner({ tone, children }: { tone: 'warning' | 'info'; children: React.ReactNode }) {
  const styles =
    tone === 'warning'
      ? 'border-amber-400/30 bg-amber-400/10 text-amber-100'
      : 'border-sky-400/30 bg-sky-400/10 text-sky-100'
  return (
    <div role="status" className={`rounded-xl border px-4 py-2.5 text-[13px] ${styles}`}>
      {children}
    </div>
  )
}

interface InterviewViewProps {
  interview: InterviewDetail
  sessionId: string
}

function InterviewView({ interview, sessionId }: InterviewViewProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isOnline = useOnlineStatus()
  const [voiceOn, setVoiceOn] = useState(true)
  const speech = useSpeechPlayback(interview.id)
  const bottomRef = useRef<HTMLDivElement>(null)

  const isRunning = interview.status === 'in_progress'

  // The reply is only shown once its voice is ready, so the text never
  // appears ahead of the audio; with voice off (or none available in
  // time) it is shown as soon as it arrives.
  const submit = useMutation({
    mutationFn: async (message: string) => {
      const turn = await api.post<InterviewTurn>(`/interview/${sessionId}/turn`, { message })
      const audio = voiceOn ? await speech.load(turn.reply) : null
      return { turn, audio }
    },
    onSuccess: ({ turn, audio }, message) => {
      const updated = appendTurn(interview, message, turn)
      queryClient.setQueryData<InterviewDetail>(['interview', sessionId], updated)
      const reply = updated.transcript.at(-1)
      if (audio && reply) speech.play(reply.index, audio)
    },
    onError: (error) => {
      // A 409 means the interview already ended (e.g. in another tab).
      if (error instanceof ApiRequestError && error.statusCode === 409) {
        void queryClient.invalidateQueries({ queryKey: ['interview', sessionId] })
      }
    },
  })
  const report = useGenerateReport(sessionId)

  const lostConnection =
    submit.error instanceof ApiRequestError && submit.error.statusCode === NETWORK_ERROR_STATUS

  // When the connection returns after dropping, resend the answer that
  // couldn't be sent. Keyed to the offline-to-online change itself, so a
  // server that stays unreachable can't trigger a resend loop; the Retry
  // button covers that case.
  const wasOffline = useRef(false)
  const unsentAnswer = submit.variables
  const resend = submit.mutate
  useEffect(() => {
    if (!isOnline) {
      wasOffline.current = true
      return
    }
    if (!wasOffline.current) return
    wasOffline.current = false
    if (lostConnection && unsentAnswer !== undefined) resend(unsentAnswer)
  }, [isOnline, lostConnection, unsentAnswer, resend])

  // A fresh interview opens with the interviewer's greeting. It is held
  // back until its voice is ready and then shown and spoken together;
  // with voice off it shows immediately.
  const opening = interview.transcript.length === 1 ? interview.transcript[0] : undefined
  const [revealedOpeningIndex, setRevealedOpeningIndex] = useState<number | null>(null)
  const openingAudio = useRef<{ index: number; audio: Promise<Blob | null> } | null>(null)
  const { load: loadSpeech, play: playSpeech } = speech
  useEffect(() => {
    if (!opening || !voiceOn || revealedOpeningIndex === opening.index) return
    let cancelled = false
    // Reused across effect re-runs so the greeting is only synthesized once.
    if (openingAudio.current?.index !== opening.index) {
      openingAudio.current = { index: opening.index, audio: loadSpeech(opening.text) }
    }
    void openingAudio.current.audio.then((audio) => {
      if (cancelled) return
      setRevealedOpeningIndex(opening.index)
      if (audio) playSpeech(opening.index, audio)
    })
    return () => {
      cancelled = true
    }
  }, [opening, voiceOn, revealedOpeningIndex, loadSpeech, playSpeech])
  const isOpeningPending = Boolean(opening) && voiceOn && revealedOpeningIndex !== opening?.index

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [interview.transcript.length, submit.isPending])

  function toggleVoice() {
    if (voiceOn) speech.stop()
    setVoiceOn((on) => !on)
  }

  return (
    <div className="h-dvh flex flex-col bg-hero">
      <InterviewHeader
        interview={interview}
        voiceOn={voiceOn}
        onToggleVoice={toggleVoice}
        isClockHeld={isOpeningPending}
        restartClock={Boolean(opening)}
      />

      <main className="scrollbar-soft [--scroll-thumb:rgba(255,255,255,0.2)] [--scroll-thumb-hover:rgba(255,255,255,0.35)] flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 sm:px-6 py-6">
          {isOpeningPending && (
            <p className="flex items-center gap-2 px-1 text-sm text-slate-400" role="status">
              <Spinner /> Your interviewer is getting ready…
            </p>
          )}
          {(isOpeningPending ? [] : interview.transcript).map((entry) => (
            <MessageBubble
              key={entry.index}
              entry={entry}
              isSpeaking={speech.playingKey === entry.index}
              onReplay={() => void speech.speak(entry.index, entry.text)}
            />
          ))}

          {submit.isPending && submit.variables !== undefined && (
            <>
              <MessageBubble
                entry={{
                  index: -1,
                  role: 'user',
                  text: submit.variables,
                  phase: interview.current_phase,
                  hint_level: null,
                  red_flag: false,
                  anxiety_detected: false,
                }}
                isSpeaking={false}
                onReplay={() => undefined}
              />
              <p className="flex items-center gap-2 px-1 text-sm text-slate-400" role="status">
                <Spinner /> Interviewer is responding…
              </p>
            </>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="border-t border-white/10 bg-hero">
        <div className="mx-auto max-w-3xl space-y-3 px-4 sm:px-6 py-4">
          {!isOnline && (
            <Banner tone="info">
              You're offline. Your answer will send automatically when the connection is back.
            </Banner>
          )}
          {interview.red_flag_warning_issued && isRunning && (
            <Banner tone="warning">
              The interviewer has flagged concerns with some of your answers. Another one will end
              the interview.
            </Banner>
          )}
          {submit.isError && isOnline && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-2.5 text-[13px] text-red-100">
              <span>
                {lostConnection
                  ? 'Connection lost. Your answer is saved here, retry to send it.'
                  : toErrorMessage(submit.error, 'Could not send your answer.')}
              </span>
              {submit.variables !== undefined && (
                <button
                  type="button"
                  onClick={() => submit.mutate(submit.variables)}
                  className="shrink-0 font-semibold underline underline-offset-2 cursor-pointer"
                >
                  Retry
                </button>
              )}
            </div>
          )}

          {isRunning ? (
            <Composer
              sessionId={interview.id}
              maxAnswerSeconds={interview.max_answer_seconds}
              isSending={submit.isPending}
              onSend={(message) => submit.mutate(message)}
              onMicStart={speech.stop}
            />
          ) : (
            <EndedPanel
              endReason={interview.end_reason}
              isGenerating={report.isPending}
              onGenerateReport={() =>
                report.mutate(undefined, {
                  onSuccess: () => navigate(`/interview/${sessionId}/report`),
                })
              }
            />
          )}
        </div>
      </footer>
    </div>
  )
}

export function InterviewChatPage() {
  const { sessionId } = useParams()
  const { data: interview, isLoading, isError, refetch } = useInterview(sessionId)

  if (isLoading) {
    return (
      <div className="h-dvh flex items-center justify-center bg-hero text-slate-300">
        <Spinner className="w-6 h-6" />
      </div>
    )
  }

  if (isError || !interview || !sessionId) {
    return (
      <div className="h-dvh flex items-center justify-center bg-hero px-6">
        <div className="max-w-md w-full">
          <ErrorState message="Couldn't load this interview." onRetry={() => refetch()} />
        </div>
      </div>
    )
  }

  return <InterviewView interview={interview} sessionId={sessionId} />
}

export default InterviewChatPage
