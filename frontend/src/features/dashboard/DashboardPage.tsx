import { Link } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { StatTile } from '../../components/ui/StatTile'
import { ChartBarIcon, CheckCircleIcon, ClockIcon, FolderIcon, SparkleIcon } from '../../components/ui/icons'
import { useAuth } from '../../lib/authContext'
import { endReasonLabel, phaseLabel, statusLabel } from '../../lib/interviewLabels'
import { useInterviews } from '../../lib/queries'
import type { InterviewSessionSummary, InterviewStatus } from '../../types/api'

const STATUS_TONE: Record<InterviewStatus, 'brand' | 'success' | 'warning'> = {
  in_progress: 'brand',
  completed: 'success',
  ended_early: 'warning',
}

function InterviewRow({ session }: { session: InterviewSessionSummary }) {
  const reportOrResumeLink =
    session.status === 'in_progress'
      ? `/interview/${session.id}`
      : `/interview/${session.id}/report`

  return (
    <Link to={reportOrResumeLink} className="block">
      <Card interactive className="flex items-center justify-between gap-4 py-4">
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-navy/10 text-navy flex items-center justify-center shrink-0">
            <ClockIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <p className="text-[14px] font-semibold text-ink truncate">
              {phaseLabel(session.current_phase)}
            </p>
            <p className="text-xs text-muted mt-0.5">
              {new Date(session.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
              {endReasonLabel(session.end_reason) && (
                <span className="text-amber-700"> · {endReasonLabel(session.end_reason)}</span>
              )}
            </p>
          </div>
        </div>
        <Badge tone={STATUS_TONE[session.status]}>{statusLabel(session.status)}</Badge>
      </Card>
    </Link>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const { data: interviews, isLoading, isError, refetch } = useInterviews()

  const total = interviews?.length ?? 0
  const inProgress = interviews?.filter((s) => s.status === 'in_progress').length ?? 0
  const completed = interviews?.filter((s) => s.status === 'completed').length ?? 0

  return (
    <AppShell>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-ink">
            Welcome back{user ? `, ${user.name.split(' ')[0]}` : ''}
          </h1>
          <p className="mt-1 text-sm text-muted">
            Pick up where you left off or run a fresh mock interview.
          </p>
        </div>
        <Link
          to="/setup"
          className="inline-flex items-center gap-2 px-5 py-3 rounded-[10px] bg-navy text-white text-[14px] font-semibold hover:bg-[#112d4e] active:scale-[0.99] transition-all shadow-sm"
        >
          <SparkleIcon className="w-4 h-4" />
          Start an interview
        </Link>
      </div>

      {!isLoading && !isError && interviews && interviews.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
          <StatTile icon={<ChartBarIcon className="w-5 h-5" />} label="Total interviews" value={total} tone="navy" />
          <StatTile icon={<ClockIcon className="w-5 h-5" />} label="In progress" value={inProgress} tone="brand" />
          <StatTile icon={<CheckCircleIcon className="w-5 h-5" />} label="Completed" value={completed} tone="success" />
        </div>
      )}

      <section className="mt-8">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-muted uppercase tracking-wide mb-3">
          <ClockIcon className="w-4 h-4" />
          Recent interviews
        </h2>

        {isLoading && <LoadingSkeleton rows={3} />}

        {isError && (
          <ErrorState
            message="Couldn't load your interviews."
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !isError && interviews && interviews.length === 0 && (
          <EmptyState
            icon={<SparkleIcon className="w-5 h-5" />}
            title="No interviews yet"
            description="Start your first mock interview to see it show up here."
            action={
              <Link
                to="/setup"
                className="text-sm font-semibold text-navy hover:underline"
              >
                Start an interview →
              </Link>
            }
          />
        )}

        {!isLoading && !isError && interviews && interviews.length > 0 && (
          <div className="space-y-3">
            {interviews.map((session) => (
              <InterviewRow key={session.id} session={session} />
            ))}
          </div>
        )}
      </section>

      <section className="mt-8">
        <Link to="/documents" className="block">
          <Card interactive className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-xl bg-brand/10 text-brand flex items-center justify-center shrink-0">
                <FolderIcon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-ink">
                  Manage your resumes and job descriptions
                </p>
                <p className="text-xs text-muted mt-0.5">
                  Review what you've uploaded so far.
                </p>
              </div>
            </div>
            <span className="text-sm font-semibold text-navy whitespace-nowrap">
              View documents →
            </span>
          </Card>
        </Link>
      </section>
    </AppShell>
  )
}
