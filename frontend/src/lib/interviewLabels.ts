import type { InterviewEndReason, InterviewPhase, InterviewStatus } from '../types/api'

const PHASE_LABELS: Record<InterviewPhase, string> = {
  background_check: 'Background Check',
  project_drill_down: 'Project Drill-Down',
  technical_interview: 'Technical Interview',
  coding_challenge: 'Coding Discussion',
  general_technical: 'General Technical',
  career_motivation: 'Career Motivation',
  candidate_questions: 'Candidate Questions',
}

export function phaseLabel(phase: InterviewPhase | string): string {
  return PHASE_LABELS[phase as InterviewPhase] ?? phase
}

const STATUS_LABELS: Record<InterviewStatus, string> = {
  in_progress: 'In progress',
  completed: 'Completed',
  ended_early: 'Ended early',
}

export function statusLabel(status: InterviewStatus): string {
  return STATUS_LABELS[status]
}

const END_REASON_LABELS: Record<NonNullable<InterviewEndReason>, string> = {
  abusive_language: 'Ended: abusive language',
  red_flag_threshold: 'Ended: too many red flags',
}

export function endReasonLabel(endReason: InterviewEndReason): string | null {
  return endReason ? END_REASON_LABELS[endReason] : null
}
