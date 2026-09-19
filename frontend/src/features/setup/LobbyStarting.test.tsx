import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LobbyStarting } from './LobbyStarting'

const STAGES = ['Reading your resume', 'Writing the first question']

describe('LobbyStarting', () => {
  it('counts down while there are seconds left', () => {
    render(<LobbyStarting secondsLeft={2} countdownTotal={3} stages={STAGES} activeStage={0} />)

    expect(screen.getByRole('timer', { name: 'Interview starting' })).toBeInTheDocument()
    expect(screen.getByText('Your interview starts in a moment')).toBeInTheDocument()
  })

  it('draws an empty ring when the countdown has no length', () => {
    render(<LobbyStarting secondsLeft={1} countdownTotal={0} stages={STAGES} activeStage={0} />)

    expect(screen.getByRole('timer')).toBeInTheDocument()
  })

  it.each([[null], [0]])('shows the preparing checklist when secondsLeft is %s', (secondsLeft) => {
    render(<LobbyStarting secondsLeft={secondsLeft} countdownTotal={3} stages={STAGES} activeStage={1} />)

    expect(screen.getByText('Preparing your interviewer')).toBeInTheDocument()
    expect(screen.getByText('Reading your resume')).toBeInTheDocument()
    expect(screen.getByText('Writing the first question')).toBeInTheDocument()
  })
})
