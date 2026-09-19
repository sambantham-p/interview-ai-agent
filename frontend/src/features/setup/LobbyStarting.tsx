import { CheckIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'

const RING_RADIUS = 54
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS

interface CountdownRingProps {
  secondsLeft: number
  total: number
}

// The ring empties one step per second, in step with the number.
function CountdownRing({ secondsLeft, total }: CountdownRingProps) {
  const progress = total === 0 ? 0 : secondsLeft / total
  return (
    <div className="relative w-36 h-36" role="timer" aria-label="Interview starting">
      <svg viewBox="0 0 128 128" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="64" cy="64" r={RING_RADIUS} fill="none" strokeWidth="8" className="stroke-mist" />
        <circle
          cx="64"
          cy="64"
          r={RING_RADIUS}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className="stroke-brand transition-[stroke-dashoffset] duration-1000 ease-linear motion-reduce:transition-none"
          strokeDasharray={RING_CIRCUMFERENCE}
          strokeDashoffset={RING_CIRCUMFERENCE * (1 - progress)}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-5xl font-bold text-ink tabular-nums">
        {secondsLeft}
      </span>
    </div>
  )
}

interface PreparingStepsProps {
  stages: string[]
  activeStage: number
}

function PreparingSteps({ stages, activeStage }: PreparingStepsProps) {
  return (
    <ol className="w-full max-w-sm space-y-3 text-left" aria-label="Preparing your interview">
      {stages.map((stage, index) => {
        const isDone = index < activeStage
        const isActive = index === activeStage
        return (
          <li
            key={stage}
            aria-current={isActive ? 'step' : undefined}
            className={`flex items-center gap-3 text-[14px] transition-colors ${
              isDone ? 'text-ink' : isActive ? 'text-ink font-semibold' : 'text-muted'
            }`}
          >
            <span
              className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                isDone ? 'bg-brand text-white' : isActive ? 'bg-navy/10 text-navy' : 'bg-[#eef2f6] text-transparent'
              }`}
            >
              {isDone ? <CheckIcon className="w-3.5 h-3.5" /> : isActive ? <Spinner className="w-3.5 h-3.5" /> : '·'}
            </span>
            {stage}
          </li>
        )
      })}
    </ol>
  )
}

interface LobbyStartingProps {
  secondsLeft: number | null
  countdownTotal: number
  stages: string[]
  activeStage: number
}

export function LobbyStarting({ secondsLeft, countdownTotal, stages, activeStage }: LobbyStartingProps) {
  const counting = secondsLeft !== null && secondsLeft > 0

  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-2xl bg-white border border-mist px-6 py-10 flex flex-col items-center gap-6 text-center"
    >
      {counting ? (
        <>
          <CountdownRing secondsLeft={secondsLeft} total={countdownTotal} />
          <div>
            <p className="text-lg font-semibold text-ink">Your interview starts in a moment</p>
            <p className="text-sm text-muted mt-1">Take a breath. The interviewer will speak first.</p>
          </div>
        </>
      ) : (
        <>
          <div>
            <p className="text-lg font-semibold text-ink">Preparing your interviewer</p>
            <p className="text-sm text-muted mt-1">This can take up to 30 seconds. Please keep this tab open.</p>
          </div>
          <PreparingSteps stages={stages} activeStage={activeStage} />
        </>
      )}
    </div>
  )
}
