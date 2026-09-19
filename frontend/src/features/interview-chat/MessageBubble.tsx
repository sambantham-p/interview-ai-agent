import { SpeakerIcon } from '../../components/ui/icons'
import type { TranscriptEntry } from '../../types/api'

interface MessageBubbleProps {
  entry: TranscriptEntry
  isSpeaking: boolean
  onReplay: () => void
}

const HINT_LABELS: Record<number, string> = {
  1: 'Small nudge',
  2: 'Hint',
  3: 'Bigger hint',
}

export function MessageBubble({ entry, isSpeaking, onReplay }: MessageBubbleProps) {
  if (entry.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand px-4 py-3 text-[15px] leading-relaxed text-[#06251f]">
          {entry.text}
        </p>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        <p className="whitespace-pre-wrap rounded-2xl rounded-bl-md border border-white/10 bg-white/6 px-4 py-3 text-[15px] leading-relaxed text-slate-100">
          {entry.text}
        </p>
        <div className="mt-1.5 flex items-center gap-2 px-1">
          <button
            type="button"
            onClick={onReplay}
            aria-label="Play this message"
            className={`p-1 rounded-md transition-colors cursor-pointer ${
              isSpeaking ? 'text-brand' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            <SpeakerIcon className={`w-4 h-4 ${isSpeaking ? 'animate-pulse' : ''}`} />
          </button>
          {entry.hint_level !== null && (
            <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-[11px] font-semibold text-amber-200">
              {HINT_LABELS[entry.hint_level] ?? 'Hint'}
            </span>
          )}
          {entry.anxiety_detected && (
            <span className="rounded-full bg-sky-400/15 px-2 py-0.5 text-[11px] font-semibold text-sky-200">
              Take your time
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
