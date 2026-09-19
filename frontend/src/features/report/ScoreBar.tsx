import { TONE_BAR, TONE_TEXT, scoreTone } from '../../lib/scoreTone'

interface ScoreBarProps {
  score: number
  label?: string
}

export function ScoreBar({ score, label }: ScoreBarProps) {
  const tone = scoreTone(score)
  return (
    <div className="flex items-center gap-3">
      <div
        className="h-2 flex-1 rounded-full bg-[#eef2f7]"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(score)}
      >
        <div
          className={`h-2 rounded-full ${TONE_BAR[tone]}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
      <span className={`w-9 text-right text-sm font-semibold tabular-nums ${TONE_TEXT[tone]}`}>
        {Math.round(score)}
      </span>
    </div>
  )
}
