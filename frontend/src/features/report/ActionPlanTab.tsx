import { Link } from 'react-router'
import { Card } from '../../components/ui/Card'
import { SparkleIcon } from '../../components/ui/icons'
import { phaseLabel } from '../../lib/interviewLabels'
import type { InterviewReport } from '../../types/api'
import { ScoreBar } from './ScoreBar'
import { evaluationsFor } from './reportInsights'

export function ActionPlanTab({ report }: { report: InterviewReport }) {
  const focusAreas = evaluationsFor(report, report.focus_dimensions)
  const hintedPhases = Object.entries(report.hint_counts).filter(([, count]) => count > 0)

  return (
    <div className="space-y-6">
      {focusAreas.length === 0 ? (
        <Card>
          <h2 className="text-[15px] font-semibold text-ink">You're in good shape</h2>
          <p className="mt-1 text-sm text-muted">
            Every dimension cleared the hiring bar. Run another interview against a different role to
            keep the edge.
          </p>
        </Card>
      ) : (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">
            Focus on these first
          </h2>
          {focusAreas.map((area, index) => (
            <Card key={area.id}>
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy/10 text-[13px] font-bold text-navy">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="text-[15px] font-semibold text-ink">{area.dimension}</h3>
                  <div className="mt-2">
                    <ScoreBar score={area.score} label={area.dimension} />
                  </div>
                  <p className="mt-3 text-sm text-muted leading-relaxed">{area.summary}</p>
                  {area.evidence[0] && (
                    <p className="mt-3 border-l-2 border-brand/40 pl-3 text-sm text-ink">
                      {area.evidence[0].reasoning}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </section>
      )}

      {(hintedPhases.length > 0 || report.red_flag_count > 0) && (
        <Card>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide">Habits to watch</h2>
          <ul className="mt-3 space-y-2 text-sm text-ink">
            {hintedPhases.map(([phase]) => (
              <li key={phase}>
                You needed hints in <strong>{phaseLabel(phase)}</strong>. Revisit those topics before
                the next round.
              </li>
            ))}
            {report.red_flag_count > 0 && (
              <li>
                {report.red_flag_count} {report.red_flag_count === 1 ? 'answer' : 'answers'} conflicted
                with your resume or sat well below the level claimed. Make sure every claim on your
                resume is one you can back up.
              </li>
            )}
          </ul>
        </Card>
      )}

      <Card className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-brand/10 text-brand flex items-center justify-center shrink-0">
            <SparkleIcon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[14px] font-semibold text-ink">Ready to try again?</p>
            <p className="text-xs text-muted mt-0.5">Pick your saved resume and job description, no re-upload.</p>
          </div>
        </div>
        <Link
          to="/setup"
          className="px-5 py-3 rounded-[10px] bg-navy text-white text-[14px] font-semibold hover:bg-[#112d4e] active:scale-[0.99] transition-all shadow-sm"
        >
          Practice again
        </Link>
      </Card>
    </div>
  )
}
