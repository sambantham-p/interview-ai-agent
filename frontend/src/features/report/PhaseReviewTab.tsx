import { useState } from 'react'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { phaseLabel } from '../../lib/interviewLabels'
import type { InterviewDetail, InterviewReport, TranscriptEntry } from '../../types/api'
import { phasesWithTranscript } from './reportInsights'

interface Citation {
  dimension: string
  reasoning: string
}

// Judge evidence keyed by the transcript message it cites.
function citationsByIndex(report: InterviewReport): Map<number, Citation[]> {
  const byIndex = new Map<number, Citation[]>()
  for (const evaluation of report.judge_evaluations) {
    for (const item of evaluation.evidence) {
      if (item.transcript_index === null) continue
      const existing = byIndex.get(item.transcript_index) ?? []
      existing.push({ dimension: evaluation.dimension, reasoning: item.reasoning })
      byIndex.set(item.transcript_index, existing)
    }
  }
  return byIndex
}

function Message({ entry, citations }: { entry: TranscriptEntry; citations: Citation[] }) {
  const isInterviewer = entry.role === 'model'
  return (
    <li className={citations.length > 0 ? 'rounded-xl bg-brand/5 border border-brand/20 p-3' : 'p-3'}>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">
        {isInterviewer ? 'Interviewer' : 'You'}
        {entry.hint_level !== null && (
          <span className="ml-2 normal-case text-amber-700">· hint {entry.hint_level}</span>
        )}
      </p>
      <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink">{entry.text}</p>
      {citations.map((citation) => (
        <p key={`${citation.dimension}-${citation.reasoning}`} className="mt-2 text-xs text-[#0d6b5f]">
          <span className="font-semibold">Cited for {citation.dimension}:</span> {citation.reasoning}
        </p>
      ))}
    </li>
  )
}

function PhaseCard({
  phase,
  entries,
  hints,
  citations,
  defaultOpen,
}: {
  phase: string
  entries: TranscriptEntry[]
  hints: number
  citations: Map<number, Citation[]>
  defaultOpen: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const citedCount = entries.filter((entry) => citations.has(entry.index)).length

  return (
    <Card className="p-0 sm:p-0">
      <button
        type="button"
        onClick={() => setOpen((isOpen) => !isOpen)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left cursor-pointer"
      >
        <span className="text-[15px] font-semibold text-ink">{phaseLabel(phase)}</span>
        <span className="flex items-center gap-2">
          {hints > 0 && <Badge tone="warning">{hints} {hints === 1 ? 'hint' : 'hints'}</Badge>}
          {citedCount > 0 && <Badge tone="brand">{citedCount} cited</Badge>}
          <span className="text-muted text-sm" aria-hidden="true">{open ? '−' : '+'}</span>
        </span>
      </button>
      {open && (
        <ul className="space-y-1 border-t border-mist px-3 py-3">
          {entries.map((entry) => (
            <Message key={entry.index} entry={entry} citations={citations.get(entry.index) ?? []} />
          ))}
        </ul>
      )}
    </Card>
  )
}

export function PhaseReviewTab({ report, detail }: { report: InterviewReport; detail: InterviewDetail }) {
  const citations = citationsByIndex(report)
  const phases = phasesWithTranscript(detail)

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        The full conversation, phase by phase. Highlighted messages are the moments the evaluation
        cites as evidence.
      </p>
      {phases.map((phase, index) => (
        <PhaseCard
          key={phase}
          phase={phase}
          entries={detail.transcript.filter((entry) => entry.phase === phase)}
          hints={report.hint_counts[phase] ?? 0}
          citations={citations}
          defaultOpen={index === 0}
        />
      ))}
    </div>
  )
}
