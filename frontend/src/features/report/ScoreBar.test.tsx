import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScoreBar } from './ScoreBar'

describe('ScoreBar', () => {
  it('exposes the rounded score as a labelled meter', () => {
    render(<ScoreBar score={82.4} label="Project Depth" />)

    const meter = screen.getByRole('meter', { name: 'Project Depth' })
    expect(meter).toHaveAttribute('aria-valuenow', '82')
    expect(screen.getByText('82')).toBeInTheDocument()
  })

  it('clamps the bar width to 0-100%', () => {
    const { container, rerender } = render(<ScoreBar score={130} />)
    expect((container.querySelector('[style]') as HTMLElement).style.width).toBe('100%')

    rerender(<ScoreBar score={-5} />)
    expect((container.querySelector('[style]') as HTMLElement).style.width).toBe('0%')
  })
})
