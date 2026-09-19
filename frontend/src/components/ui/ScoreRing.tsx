import { TONE_TEXT, scoreTone } from '../../lib/scoreTone'

const RADIUS = 52
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const RING_STROKE = {
  success: 'stroke-emerald-500',
  warning: 'stroke-amber-500',
  danger: 'stroke-red-500',
} as const

const SIZES = {
  lg: { box: 'w-36 h-36', value: 'text-4xl', stroke: 10 },
  sm: { box: 'w-16 h-16', value: 'text-lg', stroke: 12 },
} as const

interface ScoreRingProps {
  score: number
  size?: keyof typeof SIZES
}

export function ScoreRing({ score, size = 'lg' }: ScoreRingProps) {
  const tone = scoreTone(score)
  const { box, value, stroke } = SIZES[size]
  const filled = (Math.min(100, Math.max(0, score)) / 100) * CIRCUMFERENCE

  return (
    <div
      className={`relative ${box} shrink-0`}
      role="img"
      aria-label={`Overall score ${Math.round(score)} out of 100`}
    >
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle cx="60" cy="60" r={RADIUS} fill="none" strokeWidth={stroke} className="stroke-[#eef2f7]" />
        <circle
          cx="60"
          cy="60"
          r={RADIUS}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
          className={RING_STROKE[tone]}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`${value} font-bold tabular-nums ${TONE_TEXT[tone]}`}>{Math.round(score)}</span>
        {size === 'lg' && <span className="text-xs text-muted">out of 100</span>}
      </div>
    </div>
  )
}
