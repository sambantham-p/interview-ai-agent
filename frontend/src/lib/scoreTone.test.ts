import { describe, expect, it } from 'vitest'
import { scoreTone, TIER_TONE, TONE_BAR, TONE_TEXT } from './scoreTone'

describe('scoreTone', () => {
  it.each([
    [100, 'success'],
    [70, 'success'],
    [69, 'warning'],
    [55, 'warning'],
    [54, 'danger'],
    [0, 'danger'],
  ] as const)('maps %i to %s', (score, tone) => {
    expect(scoreTone(score)).toBe(tone)
  })

  it('has a text and bar class for every tone and a tone for every tier', () => {
    for (const tone of ['success', 'warning', 'danger'] as const) {
      expect(TONE_TEXT[tone]).toBeTruthy()
      expect(TONE_BAR[tone]).toBeTruthy()
    }
    expect(TIER_TONE.strong_hire).toBe('success')
    expect(TIER_TONE.no_hire).toBe('danger')
  })
})
