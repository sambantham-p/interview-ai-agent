import { CheckIcon } from './icons'

interface StepperProps {
  steps: readonly string[]
  current: number
}

// Nodes joined by connector lines; the line fills in once its step is done.
export function Stepper({ steps, current }: StepperProps) {
  return (
    <ol className="flex items-start w-full" aria-label="Setup progress">
      {steps.map((label, index) => {
        const isDone = index < current
        const isCurrent = index === current
        const isLast = index === steps.length - 1
        return (
          <li
            key={label}
            aria-current={isCurrent ? 'step' : undefined}
            className={`flex items-start ${isLast ? '' : 'flex-1'}`}
          >
            <div className="flex flex-col items-center gap-2 w-16 sm:w-20">
              <span
                className={`w-8 h-8 rounded-full flex items-center justify-center text-[13px] font-semibold border-2 transition-colors ${
                  isDone
                    ? 'bg-brand border-brand text-white'
                    : isCurrent
                      ? 'bg-white border-navy text-navy ring-4 ring-navy/10'
                      : 'bg-white border-mist text-muted'
                }`}
              >
                {isDone ? <CheckIcon className="w-4 h-4" /> : index + 1}
                {isDone && <span className="sr-only"> (completed)</span>}
              </span>
              <span
                className={`text-[12px] text-center leading-tight ${
                  isCurrent ? 'font-semibold text-ink' : isDone ? 'text-ink' : 'text-muted'
                }`}
              >
                {label}
              </span>
            </div>
            {!isLast && (
              <span
                aria-hidden="true"
                className={`flex-1 h-0.5 mt-4 -mx-2 rounded-full transition-colors ${
                  isDone ? 'bg-brand' : 'bg-mist'
                }`}
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
