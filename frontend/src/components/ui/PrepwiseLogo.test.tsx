import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PrepwiseLogo } from './PrepwiseLogo'

describe('PrepwiseLogo', () => {
  it('renders the wordmark by default', () => {
    render(<PrepwiseLogo />)
    expect(screen.getByLabelText('Prepwise')).toBeInTheDocument()
  })

  it('hides the wordmark when showWordmark is false', () => {
    render(<PrepwiseLogo showWordmark={false} />)
    expect(screen.queryByLabelText('Prepwise')).not.toBeInTheDocument()
  })

  it('uses dark text for the light variant', () => {
    render(<PrepwiseLogo variant="light" />)
    expect(screen.getByLabelText('Prepwise')).toHaveClass('text-ink')
  })

  it('renders each size variant', () => {
    const { rerender } = render(<PrepwiseLogo size="sm" />)
    expect(screen.getByLabelText('Prepwise')).toHaveClass('text-[22px]')

    rerender(<PrepwiseLogo size="lg" />)
    expect(screen.getByLabelText('Prepwise')).toHaveClass('text-[32px]')
  })
})
