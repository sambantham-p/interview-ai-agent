import { describe, it, expect } from 'vitest'
import { phaseLabel, statusLabel, endReasonLabel } from './interviewLabels'
import type { InterviewPhase, InterviewStatus } from '../types/api'

describe('phaseLabel', () => {
  const cases: [InterviewPhase, string][] = [
    ['background_check', 'Background Check'],
    ['project_drill_down', 'Project Drill-Down'],
    ['technical_interview', 'Technical Interview'],
    ['coding_challenge', 'Coding Discussion'],
    ['general_technical', 'General Technical'],
    ['career_motivation', 'Career Motivation'],
    ['candidate_questions', 'Candidate Questions'],
  ]

  it.each(cases)('phaseLabel("%s") → "%s"', (phase, expected) => {
    expect(phaseLabel(phase)).toBe(expected)
  })

  it('returns the raw string for an unknown phase key', () => {
    expect(phaseLabel('unknown_phase')).toBe('unknown_phase')
  })
})

describe('statusLabel', () => {
  const cases: [InterviewStatus, string][] = [
    ['in_progress', 'In progress'],
    ['completed', 'Completed'],
    ['ended_early', 'Ended early'],
  ]

  it.each(cases)('statusLabel("%s") → "%s"', (status, expected) => {
    expect(statusLabel(status)).toBe(expected)
  })
})

describe('endReasonLabel', () => {
  it('returns null when endReason is null', () => {
    expect(endReasonLabel(null)).toBeNull()
  })

  it('returns the correct label for abusive_language', () => {
    expect(endReasonLabel('abusive_language')).toBe('Ended: abusive language')
  })

  it('returns the correct label for red_flag_threshold', () => {
    expect(endReasonLabel('red_flag_threshold')).toBe('Ended: too many red flags')
  })
})
