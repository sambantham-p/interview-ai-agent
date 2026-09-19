import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { StatTile } from '../../components/ui/StatTile'
import {
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
} from '../../components/ui/icons'
import type { InterviewDetail, InterviewReport } from '../../types/api'
import { ScoreBar } from './ScoreBar'
import { TIER_TONE } from '../../lib/scoreTone'
import { interviewMinutes, totalHints } from './reportInsights'

interface OverviewTabProps {
  report: InterviewReport
  detail: InterviewDetail
}

export function OverviewTab({ report, detail }: OverviewTabProps) {
  const minutes = interviewMinutes(detail)

  return (
    <div className="space-y-6">
      <Card className="flex flex-col sm:flex-row items-center gap-6">
        <ScoreRing score={report.overall_score} />
        <div className="text-center sm:text-left">
          <Badge tone={TIER_TONE[report.recommendation_tier]}>
            {report.recommendation_label}
          </Badge>
          <h2 className="mt-2 text-lg font-semibold text-ink">
            Overall result
          </h2>
          <p className="mt-1 text-sm text-muted max-w-xl">{report.headline}</p>
          {report.end_reason_label && (
            <p className="mt-2 text-sm font-medium text-amber-700">
              {report.end_reason_label}
            </p>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatTile
          icon={<ClockIcon className="w-5 h-5" />}
          label="Interview length"
          value={minutes != null ? `${minutes} min` : '-'}
          tone="navy"
        />
        <StatTile
          icon={<CheckCircleIcon className="w-5 h-5" />}
          label="Hints used"
          value={totalHints(report.hint_counts)}
          tone="brand"
        />
        <StatTile
          icon={<ChartBarIcon className="w-5 h-5" />}
          label="Concerns flagged"
          value={report.red_flag_count}
          tone={report.red_flag_count > 0 ? 'warning' : 'success'}
        />
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">
          Scores by dimension
        </h2>
        {report.judge_evaluations.map((evaluation) => (
          <Card key={evaluation.id}>
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-[15px] font-semibold text-ink">
                {evaluation.dimension}
              </h3>
              <span className="text-xs text-muted">
                {Math.round(
                  (report.weights_used[evaluation.judge_name] ?? 0) * 100,
                )}
                % of overall
              </span>
            </div>
            <div className="mt-3">
              <ScoreBar score={evaluation.score} label={evaluation.dimension} />
            </div>
            <p className="mt-3 text-sm text-muted leading-relaxed">
              {evaluation.summary}
            </p>
          </Card>
        ))}
      </section>
    </div>
  )
}
