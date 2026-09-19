import { Link } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { PageIntro } from '../../components/ui/PageIntro'
import { StatTile } from '../../components/ui/StatTile'
import { ChartBarIcon, CheckCircleIcon, SparkleIcon } from '../../components/ui/icons'
import { useReports } from '../../lib/queries'
import { ReportCard } from './ReportCard'

export function ReportsPage() {
  const { data: reports, isLoading, isError, refetch } = useReports()

  const scored = (reports ?? []).flatMap((item) =>
    item.overall_score === null ? [] : [item.overall_score],
  )
  const average = scored.length
    ? Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length)
    : null

  return (
    <AppShell title="Reports">
      <PageIntro
        title="Review your interview performance"
        description="Review how you did in past interviews and see what to improve."
      />

      {scored.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
          <StatTile
            icon={<ChartBarIcon className="w-5 h-5" />}
            label="Reports"
            value={scored.length}
            tone="navy"
          />
          <StatTile
            icon={<CheckCircleIcon className="w-5 h-5" />}
            label="Average score"
            value={average ?? '-'}
            tone="brand"
          />
          <StatTile
            icon={<SparkleIcon className="w-5 h-5" />}
            label="Best score"
            value={Math.round(Math.max(...scored))}
            tone="success"
          />
        </div>
      )}

      <section className="mt-8">
        {isLoading && <LoadingSkeleton rows={4} variant="grid" />}

        {isError && (
          <ErrorState message="Couldn't load your reports." onRetry={() => refetch()} />
        )}

        {!isLoading && !isError && reports && reports.length === 0 && (
          <EmptyState
            icon={<ChartBarIcon className="w-5 h-5" />}
            title="No reports yet"
            description="Finish a mock interview and its evaluation report shows up here."
            action={
              <Link to="/setup" className="text-sm font-semibold text-navy hover:underline">
                Start an interview →
              </Link>
            }
          />
        )}

        {!isLoading && !isError && reports && reports.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {reports.map((item) => (
              <ReportCard key={item.session_id} item={item} />
            ))}
          </div>
        )}
      </section>
    </AppShell>
  )
}

export default ReportsPage
