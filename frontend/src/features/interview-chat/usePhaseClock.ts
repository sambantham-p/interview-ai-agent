import { useEffect, useState } from 'react'
import type { InterviewTurn } from '../../types/api'


export function usePhaseRemainingSeconds(turn: InterviewTurn): number | null {
  const [now, setNow] = useState(() => Date.now())
  const [receivedAt] = useState(() => Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const budgetMinutes = turn.phase_time_budget[turn.current_phase]
  if (!budgetMinutes || !turn.phase_started_at || turn.status !== 'in_progress') return null

  const elapsedAtServerMs = Date.parse(turn.server_time) - Date.parse(turn.phase_started_at)
  const elapsedMs = elapsedAtServerMs + (now - receivedAt)
  return Math.max(0, Math.round((budgetMinutes * 60_000 - elapsedMs) / 1000))
}

export function formatClock(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
