import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from './ToastProvider'
import { useToast } from './toastContext'

function Trigger() {
  const { showToast } = useToast()
  return (
    <>
      <button onClick={() => showToast('Saved')}>ok</button>
      <button onClick={() => showToast('Broke', 'error')}>fail</button>
    </>
  )
}

describe('ToastProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows a success toast as a status and removes it after the timeout', () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    )

    act(() => screen.getByText('ok').click())
    expect(screen.getByRole('status')).toHaveTextContent('Saved')

    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(screen.queryByText('Saved')).not.toBeInTheDocument()
  })

  it('shows an error toast as an alert', () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    )

    act(() => screen.getByText('fail').click())
    expect(screen.getByRole('alert')).toHaveTextContent('Broke')
  })

  it('throws when useToast is used outside a provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<Trigger />)).toThrow('useToast must be used within a ToastProvider')
    spy.mockRestore()
  })
})
