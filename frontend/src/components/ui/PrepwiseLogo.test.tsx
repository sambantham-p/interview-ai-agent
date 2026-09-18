import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PrepwiseLogo } from './PrepwiseLogo'

describe('PrepwiseLogo', () => {
  it('renders the wordmark by default', () => {
    render(<PrepwiseLogo />)
    expect(screen.getByText('Prepwise')).toBeInTheDocument()
  })

  it('hides the wordmark when showWordmark is false', () => {
    render(<PrepwiseLogo showWordmark={false} />)
    expect(screen.queryByText('Prepwise')).not.toBeInTheDocument()
  })

  it('uses dark text for the light variant', () => {
    render(<PrepwiseLogo variant="light" />)
    expect(screen.getByText('Prepwise')).toHaveClass('text-ink')
  })

  it('renders each size variant', () => {
    const { rerender } = render(<PrepwiseLogo size="sm" />)
    expect(screen.getByText('Prepwise')).toHaveClass('text-lg')

    rerender(<PrepwiseLogo size="lg" />)
    expect(screen.getByText('Prepwise')).toHaveClass('text-2xl')
  })
})
