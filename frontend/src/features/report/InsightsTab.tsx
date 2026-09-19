import { Card } from '../../components/ui/Card'
import { CheckCircleIcon, SparkleIcon } from '../../components/ui/icons'
import { phaseLabel } from '../../lib/interviewLabels'
import type { InterviewReport, JudgeEvaluation } from '../../types/api'
import { ScoreBar } from './ScoreBar'
import { evaluationsFor, rankedByScore, weightedPoints } from './reportInsights'

function InsightList({
  title,
  icon,
  emptyText,
  items,
}: {
  title: string
  icon: React.ReactNode
  emptyText: string
  items: JudgeEvaluation[]
}) {
  return (
    <Card>
      <h3 className="flex items-center gap-2 text-sm font-semibold text-muted uppercase tracking-wide">
        {icon}
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-muted">{emptyText}</p>
      ) : (
        <ul className="mt-3 space-y-4">
          {items.map((item) => (
            <li key={item.id}>
              <p className="text-[15px] font-semibold text-ink">
                {item.dimension} <span className="text-muted font-normal">· {Math.round(item.score)}</span>
              </p>
              <p className="mt-1 text-sm text-muted leading-relaxed">{item.summary}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function InsightsTab({ report }: { report: InterviewReport }) {
  const evaluations = report.judge_evaluations
  const hintEntries = Object.entries(report.hint_counts).filter(([, count]) => count > 0)

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <InsightList
          title="Strengths"
          icon={<CheckCircleIcon className="w-4 h-4" />}
          emptyText="No dimension reached the hiring bar this time."
          items={evaluationsFor(report, report.strength_dimensions)}
        />
        <InsightList
          title="Areas to improve"
          icon={<SparkleIcon className="w-4 h-4" />}
          emptyText="Every dimension cleared the hiring bar."
          items={evaluationsFor(report, report.focus_dimensions)}
        />
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-muted uppercase tracking-wide">
          What drove your overall score
        </h3>
        <p className="mt-1 text-sm text-muted">
          Points each dimension contributed, after its weight.
        </p>
        <ul className="mt-4 space-y-4">
          {rankedByScore(evaluations).map((evaluation) => {
            const weight = report.weights_used[evaluation.judge_name] ?? 0
            return (
              <li key={evaluation.id}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-medium text-ink">{evaluation.dimension}</span>
                  <span className="text-xs text-muted tabular-nums">
                    {weightedPoints(evaluation, report).toFixed(1)} of {Math.round(weight * 100)} pts
                  </span>
                </div>
                <div className="mt-1.5">
                  <ScoreBar score={evaluation.score} label={evaluation.dimension} />
                </div>
              </li>
            )
          })}
        </ul>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-muted uppercase tracking-wide">Hints by phase</h3>
        {hintEntries.length === 0 ? (
          <p className="mt-3 text-sm text-muted">You didn't need any hints. Nicely done.</p>
        ) : (
          <ul className="mt-3 divide-y divide-mist">
            {hintEntries.map(([phase, count]) => (
              <li key={phase} className="flex items-center justify-between py-2.5 text-sm">
                <span className="text-ink">{phaseLabel(phase)}</span>
                <span className="font-semibold tabular-nums text-amber-700">
                  {count} {count === 1 ? 'hint' : 'hints'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
