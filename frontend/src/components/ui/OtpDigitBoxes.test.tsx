import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { OtpDigitBoxes } from './OtpDigitBoxes'

describe('OtpDigitBoxes', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('rejects non-numeric input', () => {
    const onChange = vi.fn()
    render(<OtpDigitBoxes value="" onChange={onChange} />)
    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'a' } })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('calls onComplete once all 6 digits are entered', () => {
    const onChange = vi.fn()
    const onComplete = vi.fn()
    const { rerender } = render(
      <OtpDigitBoxes value="12345" onChange={onChange} onComplete={onComplete} />
    )
    fireEvent.change(screen.getAllByRole('textbox')[5], { target: { value: '6' } })

    expect(onChange).toHaveBeenCalledWith('123456')
    rerender(<OtpDigitBoxes value="123456" onChange={onChange} onComplete={onComplete} />)
    expect(onComplete).toHaveBeenCalledWith('123456')
  })

  it('moves focus to the next box after entering a digit', () => {
    render(<OtpDigitBoxes value="" onChange={vi.fn()} />)
    const inputs = screen.getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: '5' } })
    expect(inputs[1]).toHaveFocus()
  })

  it('moves focus to the previous box on Backspace when the current box is empty', () => {
    render(<OtpDigitBoxes value="1" onChange={vi.fn()} />)
    const inputs = screen.getAllByRole('textbox')
    inputs[1].focus()
    fireEvent.keyDown(inputs[1], { key: 'Backspace' })
    expect(inputs[0]).toHaveFocus()
  })

  it('does nothing on Backspace at the first box', () => {
    render(<OtpDigitBoxes value="" onChange={vi.fn()} />)
    const inputs = screen.getAllByRole('textbox')
    inputs[0].focus()
    expect(() => fireEvent.keyDown(inputs[0], { key: 'Backspace' })).not.toThrow()
    expect(inputs[0]).toHaveFocus()
  })

  it('accepts a pasted 6-digit code and calls onComplete', () => {
    const onChange = vi.fn()
    const onComplete = vi.fn()
    render(<OtpDigitBoxes value="" onChange={onChange} onComplete={onComplete} />)

    const container = screen.getAllByRole('textbox')[0].parentElement as HTMLElement
    fireEvent.paste(container, {
      clipboardData: { getData: () => '987654' },
    })

    expect(onChange).toHaveBeenCalledWith('987654')
    expect(onComplete).toHaveBeenCalledWith('987654')
  })

  it('accepts a pasted code without requiring an onComplete callback', () => {
    const onChange = vi.fn()
    render(<OtpDigitBoxes value="" onChange={onChange} />)

    const container = screen.getAllByRole('textbox')[0].parentElement as HTMLElement
    expect(() =>
      fireEvent.paste(container, { clipboardData: { getData: () => '111222' } })
    ).not.toThrow()

    expect(onChange).toHaveBeenCalledWith('111222')
  })

  it('ignores a pasted value that is not exactly 6 digits', () => {
    const onChange = vi.fn()
    render(<OtpDigitBoxes value="" onChange={onChange} />)

    const container = screen.getAllByRole('textbox')[0].parentElement as HTMLElement
    fireEvent.paste(container, {
      clipboardData: { getData: () => '12ab' },
    })

    expect(onChange).not.toHaveBeenCalled()
  })

  it('counts down the resend timer and disables resend until it reaches zero', () => {
    const onResend = vi.fn()
    render(<OtpDigitBoxes value="" onChange={vi.fn()} onResend={onResend} />)

    expect(screen.getByText(/Resend code in 00:45/)).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(45_000)
    })
    expect(screen.getByText('Resend code now')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Resend code now'))
    expect(onResend).toHaveBeenCalled()
    expect(screen.getByText(/Resend code in 00:45/)).toBeInTheDocument()
  })

  it('does nothing when resend is clicked with no onResend callback provided', () => {
    render(<OtpDigitBoxes value="" onChange={vi.fn()} />)
    act(() => {
      vi.advanceTimersByTime(45_000)
    })
    expect(() => fireEvent.click(screen.getByText('Resend code now'))).not.toThrow()
  })

  it('shows a sending state while isResending is true', () => {
    render(<OtpDigitBoxes value="" onChange={vi.fn()} onResend={vi.fn()} isResending />)
    act(() => {
      vi.advanceTimersByTime(45_000)
    })
    expect(screen.getByText('Sending...')).toBeInTheDocument()
    expect(screen.getByText('Sending...')).toBeDisabled()
  })

  it('renders a change-email link only when onChangeEmail is provided', () => {
    const onChangeEmail = vi.fn()
    const { rerender } = render(<OtpDigitBoxes value="" onChange={vi.fn()} />)
    expect(screen.queryByText('Change email address')).not.toBeInTheDocument()

    rerender(<OtpDigitBoxes value="" onChange={vi.fn()} onChangeEmail={onChangeEmail} />)
    fireEvent.click(screen.getByText('Change email address'))
    expect(onChangeEmail).toHaveBeenCalled()
  })
})
