import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { LoadingSkeleton } from './LoadingSkeleton'

describe('LoadingSkeleton', () => {
  it('renders the requested number of row placeholders by default', () => {
    render(<LoadingSkeleton rows={3} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders a 2-up grid of card placeholders for the grid variant', () => {
    const { container } = render(<LoadingSkeleton rows={2} variant="grid" />)
    expect(container.querySelector('.grid-cols-1')).toBeInTheDocument()
  })
})
