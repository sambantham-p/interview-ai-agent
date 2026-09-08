import { useParams } from 'react-router'

// Placeholder — cached useQuery against GET /sessions/:id/report once the
// Stage 5 Judge agents + report endpoint exist (see root CLAUDE.md).
export function ReportPage() {
  const { sessionId } = useParams()

  return (
    <div className="mx-auto max-w-2xl p-8">
      <h2 className="text-xl font-semibold text-slate-900">
        Report — session {sessionId}
      </h2>
      <p className="mt-2 text-slate-600">
        Placeholder page. Will show per-dimension scores with cited
        transcript evidence once the Stage 5 report endpoint exists.
      </p>
    </div>
  )
}

export default ReportPage
