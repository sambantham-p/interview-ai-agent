import { Link } from 'react-router'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { DocumentIcon } from '../../components/ui/icons'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { TIER_TONE } from '../../lib/scoreTone'
import type { ReportListItem } from '../../types/api'

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}

export function ReportCard({ item }: { item: ReportListItem }) {
  const hasReport = item.overall_score !== null && item.recommendation_tier !== null
  const date = new Date(item.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <Link to={`/interview/${item.session_id}/report`} className="block h-full">
      <Card interactive className="h-full flex items-center gap-4">
        {hasReport ? (
          <ScoreRing score={item.overall_score!} size="sm" />
        ) : (
          <div className="w-16 h-16 shrink-0 rounded-full border border-dashed border-hairline text-faint flex items-center justify-center">
            <DocumentIcon className="w-6 h-6" />
          </div>
        )}

        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-semibold text-ink truncate">{item.job_role}</p>
          <p className="mt-0.5 text-xs text-muted truncate">
            {item.company_name ? `${item.company_name} · ` : ''}
            {date}
            {item.duration_minutes !== null ? ` · ${item.duration_minutes} min` : ''}
          </p>

          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            {hasReport ? (
              <Badge tone={TIER_TONE[item.recommendation_tier!]}>{item.recommendation_label}</Badge>
            ) : (
              <Badge>Report not generated</Badge>
            )}
            {item.end_reason_label && <Badge tone="warning">{item.end_reason_label}</Badge>}
            {item.hint_count > 0 && <Badge tone="navy">{plural(item.hint_count, 'hint')}</Badge>}
            {item.red_flag_count > 0 && (
              <Badge tone="danger">{plural(item.red_flag_count, 'flag')}</Badge>
            )}
          </div>
        </div>

        <span className="hidden sm:block shrink-0 text-sm font-semibold text-navy whitespace-nowrap">
          {hasReport ? 'View report →' : 'Generate →'}
        </span>
      </Card>
    </Link>
  )
}
