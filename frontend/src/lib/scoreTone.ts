import type { RecommendationTier } from '../types/api'

export type ScoreTone = 'success' | 'warning' | 'danger'


const GOOD_SCORE = 70
const FAIR_SCORE = 55

export function scoreTone(score: number): ScoreTone {
  if (score >= GOOD_SCORE) return 'success'
  if (score >= FAIR_SCORE) return 'warning'
  return 'danger'
}

export const TONE_TEXT: Record<ScoreTone, string> = {
  success: 'text-emerald-600',
  warning: 'text-amber-600',
  danger: 'text-red-600',
}

export const TONE_BAR: Record<ScoreTone, string> = {
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
}

export const TIER_TONE: Record<RecommendationTier, ScoreTone> = {
  strong_hire: 'success',
  hire: 'success',
  borderline: 'warning',
  no_hire: 'danger',
}
