import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RootErrorBoundary } from './RootErrorBoundary'

function Boom(): React.ReactElement {
  throw new Error('render crash')
}

describe('RootErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders its children when nothing fails', () => {
    render(
      <RootErrorBoundary>
        <p>All good</p>
      </RootErrorBoundary>,
    )

    expect(screen.getByText('All good')).toBeInTheDocument()
  })

  it('shows a fallback and logs when a child crashes', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <RootErrorBoundary>
        <Boom />
      </RootErrorBoundary>,
    )

    expect(screen.getByText('Something went wrong.')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledWith('Unhandled render error', expect.any(Error), expect.any(String))
  })
})
