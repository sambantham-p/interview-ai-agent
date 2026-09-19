import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScoreRing } from './ScoreRing'

describe('ScoreRing', () => {
  it('announces the rounded score', () => {
    render(<ScoreRing score={74.6} />)

    expect(screen.getByRole('img', { name: 'Overall score 75 out of 100' })).toBeInTheDocument()
  })

  it('renders the small size and clamps out-of-range scores', () => {
    const { container, rerender } = render(<ScoreRing score={150} size="sm" />)
    expect(container.firstElementChild?.className).toContain('w-16')

    rerender(<ScoreRing score={-20} size="sm" />)
    expect(screen.getByRole('img')).toBeInTheDocument()
  })
})
