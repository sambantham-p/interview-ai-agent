import type { InterviewDetail, InterviewReport, JudgeEvaluation } from '../../types/api'

export function rankedByScore(evaluations: JudgeEvaluation[]): JudgeEvaluation[] {
  return [...evaluations].sort((a, b) => b.score - a.score)
}


export function evaluationsFor(report: InterviewReport, judgeNames: string[]): JudgeEvaluation[] {
  return judgeNames
    .map((name) => report.judge_evaluations.find((e) => e.judge_name === name))
    .filter((e): e is JudgeEvaluation => e !== undefined)
}

// How many points of the overall score a dimension contributed.
export function weightedPoints(evaluation: JudgeEvaluation, report: InterviewReport): number {
  return evaluation.score * (report.weights_used[evaluation.judge_name] ?? 0)
}

export function totalHints(hintCounts: Record<string, number>): number {
  return Object.values(hintCounts).reduce((sum, count) => sum + count, 0)
}

export function interviewMinutes(detail: InterviewDetail): number | null {
  if (!detail.ended_at) return null
  const minutes = (Date.parse(detail.ended_at) - Date.parse(detail.created_at)) / 60_000
  return Math.max(1, Math.round(minutes))
}

// The phases that actually have conversation, in the order they happened.
export function phasesWithTranscript(detail: InterviewDetail): string[] {
  const seen: string[] = []
  for (const entry of detail.transcript) {
    if (entry.phase && !seen.includes(entry.phase)) seen.push(entry.phase)
  }
  return seen
}
