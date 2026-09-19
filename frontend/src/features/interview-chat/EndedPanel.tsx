import { Link } from 'react-router'
import { Spinner } from '../../components/ui/Spinner'
import type { InterviewEndReason } from '../../types/api'

interface EndedPanelProps {
  endReason: InterviewEndReason
  isGenerating: boolean
  onGenerateReport: () => void
}

const HEADLINES: Record<'completed' | NonNullable<InterviewEndReason>, { title: string; body: string }> = {
  completed: {
    title: 'Interview complete',
    body: 'Thanks for your time. Your evaluation report is built from the full conversation.',
  },
  abusive_language: {
    title: 'Interview ended',
    body: 'This interview was ended because of the language used. It has been noted in your evaluation.',
  },
  red_flag_threshold: {
    title: 'Interview ended early',
    body: 'Too many answers conflicted with your resume or fell well short of the level claimed, so the interview stopped early. Your report explains what came up.',
  },
}

export function EndedPanel({ endReason, isGenerating, onGenerateReport }: EndedPanelProps) {
  const { title, body } = HEADLINES[endReason ?? 'completed']

  return (
    <div className="space-y-4 rounded-2xl border border-white/10 bg-white/6 p-5 text-center">
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <p className="mt-1 text-sm text-slate-300">{body}</p>
      </div>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        <button
          type="button"
          onClick={onGenerateReport}
          disabled={isGenerating}
          className="inline-flex items-center justify-center gap-2 rounded-[10px] bg-brand px-6 py-3 text-[15px] font-semibold text-[#06251f] hover:bg-[#14c3a8] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isGenerating ? (
            <>
              <Spinner /> Evaluating your interview…
            </>
          ) : (
            'View my report'
          )}
        </button>
        <Link to="/dashboard" className="text-sm font-semibold text-slate-300 hover:text-white">
          Back to dashboard
        </Link>
      </div>
    </div>
  )
}
