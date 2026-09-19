import { describe, expect, it } from 'vitest'
import { buildDetail, buildTurn } from '../../test/fixtures'
import { appendTurn } from './interviewTranscript'

describe('appendTurn', () => {
  it('adds the candidate answer and the interviewer reply and merges the turn state', () => {
    const session = buildDetail()
    const turn = buildTurn({
      reply: 'Next question.',
      hint_level: 2,
      red_flag: true,
      anxiety_detected: true,
      status: 'completed',
    })

    const next = appendTurn(session, 'My answer', turn)

    expect(next.status).toBe('completed')
    expect(next.transcript).toHaveLength(4)
    expect(next.transcript[2]).toMatchObject({ index: 3, role: 'user', text: 'My answer' })
    expect(next.transcript[3]).toMatchObject({
      index: 4,
      role: 'model',
      text: 'Next question.',
      hint_level: 2,
      red_flag: true,
      anxiety_detected: true,
    })
  })

  it('starts numbering from 1 when the transcript is empty', () => {
    const next = appendTurn(buildDetail({ transcript: [] }), 'Hi', buildTurn())

    expect(next.transcript.map((entry) => entry.index)).toEqual([1, 2])
  })
})
