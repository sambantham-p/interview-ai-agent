import { act, render, renderHook, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buildDetail, buildTurn } from '../../test/fixtures'
import { InterviewHeader } from './InterviewHeader'
import { formatClock, usePhaseRemainingSeconds } from './usePhaseClock'

describe('formatClock', () => {
  it('formats seconds as m:ss', () => {
    expect(formatClock(0)).toBe('0:00')
    expect(formatClock(65)).toBe('1:05')
    expect(formatClock(600)).toBe('10:00')
  })
})

describe('usePhaseRemainingSeconds', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T10:01:00Z'))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('counts down from the budget minus the time already spent in the phase', () => {
    // budget 8 min, 1 min elapsed at the server -> 7:00 left
    const { result } = renderHook(() => usePhaseRemainingSeconds(buildTurn()))
    expect(result.current).toBe(420)

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(result.current).toBe(415)
  })

  it('never goes below zero', () => {
    const { result } = renderHook(() =>
      usePhaseRemainingSeconds(buildTurn({ server_time: '2026-01-01T11:00:00Z' })),
    )

    expect(result.current).toBe(0)
  })

  it.each([
    ['there is no budget for the phase', { phase_time_budget: {} }],
    ['the phase has not started', { phase_started_at: null }],
    ['the interview is not running', { status: 'completed' as const }],
  ])('returns null when %s', (_label, overrides) => {
    const { result } = renderHook(() => usePhaseRemainingSeconds(buildTurn(overrides)))

    expect(result.current).toBeNull()
  })
})

describe('InterviewHeader', () => {
  function renderHeader(overrides = {}, voiceOn = true) {
    const onToggleVoice = vi.fn<(...args: unknown[]) => unknown>()
    render(
      <MemoryRouter>
        <InterviewHeader
          interview={buildDetail(overrides)}
          voiceOn={voiceOn}
          onToggleVoice={onToggleVoice}
        />
      </MemoryRouter>,
    )
    return { onToggleVoice }
  }

  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T10:01:00Z'))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the role, company, phase progress and the time left', () => {
    renderHeader()

    expect(screen.getByText('Backend Engineer · Acme')).toBeInTheDocument()
    expect(screen.getByText('Phase 1 of 2 · Background Check')).toBeInTheDocument()
    expect(screen.getByLabelText('Time left in this phase')).toHaveTextContent('7:00')
    expect(screen.getByRole('link', { name: 'Leave the interview' })).toHaveAttribute('href', '/dashboard')
  })

  it('omits the company and phase number when they are unknown', () => {
    renderHeader({ company_name: null, selected_phases: ['technical_interview'], phase_time_budget: {} })

    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
    expect(screen.getByText('Background Check')).toBeInTheDocument()
    expect(screen.queryByLabelText('Time left in this phase')).not.toBeInTheDocument()
  })

  it('warns when time is running low and says wrapping up at zero', () => {
    renderHeader({ phase_time_status: 'running_low', server_time: '2026-01-01T11:00:00Z' })

    const chip = screen.getByLabelText('Time left in this phase')
    expect(chip).toHaveTextContent('Wrapping up')
    expect(chip).toHaveClass('text-amber-200')
  })

  it('marks earlier phases as done in the progress bar', () => {
    renderHeader({ current_phase: 'technical_interview' })

    expect(screen.getByText('Phase 2 of 2 · Technical Interview')).toBeInTheDocument()
  })

  it('toggles the interviewer voice', () => {
    const { onToggleVoice } = renderHeader({}, true)

    screen.getByRole('button', { name: 'Mute interviewer voice' }).click()

    expect(onToggleVoice).toHaveBeenCalledOnce()
  })

  it('offers to unmute when the voice is off', () => {
    renderHeader({}, false)

    expect(screen.getByRole('button', { name: 'Unmute interviewer voice' })).toHaveAttribute('aria-pressed', 'false')
  })
})
