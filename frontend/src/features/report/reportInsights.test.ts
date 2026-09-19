import { describe, expect, it } from 'vitest'
import { buildDetail, buildEntry, buildEvaluation, buildReport } from '../../test/fixtures'
import {
  evaluationsFor,
  interviewMinutes,
  phasesWithTranscript,
  rankedByScore,
  totalHints,
  weightedPoints,
} from './reportInsights'

describe('reportInsights', () => {
  const report = buildReport()

  it('ranks evaluations from best to worst without mutating the input', () => {
    const input = [...report.judge_evaluations].reverse()
    const ranked = rankedByScore(input)

    expect(ranked.map((e) => e.judge_name)).toEqual(['project_depth', 'coding'])
    expect(input[0].judge_name).toBe('coding')
  })

  it('picks evaluations by judge name and skips unknown names', () => {
    expect(evaluationsFor(report, ['coding', 'nope']).map((e) => e.judge_name)).toEqual(['coding'])
  })

  it('weights points by the weight the report used, defaulting to zero', () => {
    expect(weightedPoints(report.judge_evaluations[0], report)).toBeCloseTo(20.5)
    expect(weightedPoints(buildEvaluation({ judge_name: 'other' }), report)).toBe(0)
  })

  it('sums hints', () => {
    expect(totalHints({ a: 1, b: 3 })).toBe(4)
    expect(totalHints({})).toBe(0)
  })

  it('computes interview minutes, at least one, or null while unfinished', () => {
    expect(interviewMinutes(buildDetail())).toBeNull()
    expect(
      interviewMinutes(buildDetail({ ended_at: '2026-01-01T10:30:00Z' })),
    ).toBe(30)
    expect(interviewMinutes(buildDetail({ ended_at: '2026-01-01T10:00:05Z' }))).toBe(1)
  })

  it('lists transcript phases once each in order, ignoring entries without a phase', () => {
    const detail = buildDetail({
      transcript: [
        buildEntry({ index: 1, phase: 'technical_interview' }),
        buildEntry({ index: 2, phase: 'background_check' }),
        buildEntry({ index: 3, phase: 'technical_interview' }),
        buildEntry({ index: 4, phase: null }),
      ],
    })

    expect(phasesWithTranscript(detail)).toEqual(['technical_interview', 'background_check'])
  })
})
