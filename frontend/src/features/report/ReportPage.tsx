import { Link, useParams } from 'react-router'
import { AppShell } from '../../components/AppShell'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton'
import { Spinner } from '../../components/ui/Spinner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/Tabs'
import {
  ChartBarIcon,
  CheckCircleIcon,
  DocumentIcon,
  DownloadIcon,
  SparkleIcon,
} from '../../components/ui/icons'
import { ApiRequestError } from '../../lib/api'
import { useGenerateReport, useInterview, useInterviewReport } from '../../lib/queries'
import type { InterviewDetail, InterviewReport } from '../../types/api'
import { ActionPlanTab } from './ActionPlanTab'
import { InsightsTab } from './InsightsTab'
import { OverviewTab } from './OverviewTab'
import { PhaseReviewTab } from './PhaseReviewTab'
import { TIER_TONE } from '../../lib/scoreTone'
import { useReportPdfDownload } from './useReportPdfDownload'

const TABS = [
  { id: 'overview', label: 'Overview', icon: <ChartBarIcon className="w-4.5 h-4.5" /> },
  { id: 'insights', label: 'Performance insights', icon: <SparkleIcon className="w-4.5 h-4.5" /> },
  { id: 'phases', label: 'Phase review', icon: <DocumentIcon className="w-4.5 h-4.5" /> },
  { id: 'plan', label: 'Action plan', icon: <CheckCircleIcon className="w-4.5 h-4.5" /> },
]

function ReportView({
  report,
  detail,
  sessionId,
}: {
  report: InterviewReport
  detail: InterviewDetail
  sessionId: string
}) {
  const pdf = useReportPdfDownload(sessionId)

  return (
    <>
      <div className="rounded-2xl bg-hero px-6 py-6 sm:px-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-5">
        <div className="min-w-0">
          <Badge tone={TIER_TONE[report.recommendation_tier]}>{report.recommendation_label}</Badge>
          <h2 className="mt-3 text-2xl font-bold text-white truncate">{detail.job_role}</h2>
          <p className="mt-1 text-sm text-slate-400">
            {detail.company_name ? `${detail.company_name} · ` : ''}
            {new Date(detail.created_at).toLocaleDateString(undefined, {
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => pdf.mutate()}
            disabled={pdf.isPending}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-[10px] bg-brand text-[#06251f] text-[14px] font-semibold hover:bg-[#14c3a8] active:scale-[0.99] transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {pdf.isPending ? <Spinner /> : <DownloadIcon className="w-4 h-4" />}
            Download PDF
          </button>
          <Link
            to="/setup"
            className="inline-flex items-center px-5 py-3 rounded-[10px] bg-white/5 border border-white/20 text-white text-[14px] font-semibold hover:bg-white/10 transition-all"
          >
            Practice again
          </Link>
        </div>
      </div>

      <Tabs defaultValue="overview" className="mt-6">
        <TabsList label="Report sections">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} icon={tab.icon}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="overview">
          <OverviewTab report={report} detail={detail} />
        </TabsContent>
        <TabsContent value="insights">
          <InsightsTab report={report} />
        </TabsContent>
        <TabsContent value="phases">
          <PhaseReviewTab report={report} detail={detail} />
        </TabsContent>
        <TabsContent value="plan">
          <ActionPlanTab report={report} />
        </TabsContent>
      </Tabs>
    </>
  )
}

function NoReportYet({ detail, sessionId }: { detail: InterviewDetail; sessionId: string }) {
  const generate = useGenerateReport(sessionId)

  if (detail.status === 'in_progress') {
    return (
      <EmptyState
        icon={<ChartBarIcon className="w-5 h-5" />}
        title="This interview isn't finished yet"
        description="Your report is available once the interview is complete."
        action={
          <Link to={`/interview/${sessionId}`} className="text-sm font-semibold text-navy hover:underline">
            Continue the interview →
          </Link>
        }
      />
    )
  }

  return (
    <EmptyState
      icon={<ChartBarIcon className="w-5 h-5" />}
      title="Your report hasn't been generated yet"
      description="Five evaluators review the full conversation and score it. This takes a short while."
      action={
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-[10px] bg-navy text-white text-[14px] font-semibold hover:bg-[#112d4e] transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {generate.isPending ? (
              <>
                <Spinner /> Evaluating your interview…
              </>
            ) : (
              'Generate my report'
            )}
          </button>
        </div>
      }
    />
  )
}

export function ReportPage() {
  const { sessionId } = useParams()
  const detailQuery = useInterview(sessionId)
  const reportQuery = useInterviewReport(sessionId)

  const isLoading = detailQuery.isLoading || reportQuery.isLoading
  const reportMissing =
    reportQuery.error instanceof ApiRequestError && reportQuery.error.statusCode === 404
  const detail = detailQuery.data

  return (
    <AppShell title="Interview report" parent={{ label: 'Reports', to: '/reports' }}>
      {isLoading && <LoadingSkeleton rows={3} />}

      {!isLoading && (detailQuery.isError || !detail || !sessionId) && (
        <ErrorState message="Couldn't load this interview." onRetry={() => detailQuery.refetch()} />
      )}

      {!isLoading && detail && sessionId && reportQuery.data && (
        <ReportView report={reportQuery.data} detail={detail} sessionId={sessionId} />
      )}

      {!isLoading && detail && sessionId && !reportQuery.data && reportMissing && (
        <NoReportYet detail={detail} sessionId={sessionId} />
      )}

      {!isLoading && detail && !reportQuery.data && reportQuery.isError && !reportMissing && (
        <ErrorState message="Couldn't load the report." onRetry={() => reportQuery.refetch()} />
      )}
    </AppShell>
  )
}

export default ReportPage
