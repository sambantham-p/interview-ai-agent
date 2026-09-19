import { screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { VerifyOtpPage } from './VerifyOtpPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockVerifyOtp, mockResendOtp } = vi.hoisted(() => ({
  mockVerifyOtp: vi.fn<(...args: unknown[]) => unknown>(),
  mockResendOtp: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    verifyOtp: mockVerifyOtp,
    resendOtp: mockResendOtp,
  }),
}))

function renderVerify(search = '', state?: unknown) {
  renderWithQueryClient(
    <MemoryRouter initialEntries={[{ pathname: '/verify-email', search, state }]}>
      <Routes>
        <Route path="/verify-email" element={<VerifyOtpPage />} />
        <Route path="/setup" element={<div>Setup Page</div>} />
        <Route path="/signup" element={<div>Signup Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

// Fake timers must be active *before* the component mounts (OtpDigitBoxes'
// countdown interval is a real timer otherwise, and switching to fake
// timers afterward doesn't retroactively adopt it). Scoped to just the
// resend tests, and switched back to real timers before any `waitFor` -
// testing-library's own polling needs real timers to resolve.
function renderVerifyWithResendReady(search = '', state?: unknown) {
  vi.useFakeTimers()
  renderVerify(search, state)
  act(() => {
    vi.advanceTimersByTime(45_000)
  })
  vi.useRealTimers()
}

function enterOtp(code: string) {
  const inputs = screen.getAllByRole('textbox')
  code.split('').forEach((digit, i) => {
    fireEvent.change(inputs[i], { target: { value: digit } })
  })
}

describe('VerifyOtpPage', () => {
  beforeEach(() => {
    mockVerifyOtp.mockReset()
    mockResendOtp.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reads the email from the query string', () => {
    renderVerify('?email=alex%40prepwise.ai')
    expect(screen.getByText('alex@prepwise.ai')).toBeInTheDocument()
  })

  it('verifies the code, shows the success state, then navigates to /setup', async () => {
    mockVerifyOtp.mockResolvedValueOnce(undefined)
    renderVerify('?email=alex%40prepwise.ai')

    // Entering the 6th digit auto-triggers verification via
    // OtpDigitBoxes' onComplete - no separate button click needed.
    enterOtp('123456')

    await waitFor(() => expect(screen.getByText('Email verified')).toBeInTheDocument())
    expect(mockVerifyOtp).toHaveBeenCalledWith('alex@prepwise.ai', '123456')

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Prepwise' }))
    expect(screen.getByText('Setup Page')).toBeInTheDocument()
  })

  it('keeps Verify email disabled for an incomplete code', () => {
    renderVerify('?email=alex%40prepwise.ai')
    enterOtp('123')
    expect(screen.getByRole('button', { name: 'Verify email' })).toBeDisabled()
  })

  it('shows the error message from a failed verification', async () => {
    mockVerifyOtp.mockRejectedValueOnce(new Error('Incorrect verification code.'))
    renderVerify('?email=alex%40prepwise.ai')

    enterOtp('123456')

    await waitFor(() =>
      expect(screen.getByText('Incorrect verification code.')).toBeInTheDocument()
    )
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockVerifyOtp.mockRejectedValueOnce('not an Error instance')
    renderVerify('?email=alex%40prepwise.ai')

    enterOtp('123456')

    await waitFor(() =>
      expect(screen.getByText('Invalid verification code.')).toBeInTheDocument()
    )
  })

  it('shows a missing-email error when no email is present', async () => {
    renderVerify()
    enterOtp('123456')

    await waitFor(() =>
      expect(
        screen.getByText('Missing email address. Please sign up again.')
      ).toBeInTheDocument()
    )
    expect(mockVerifyOtp).not.toHaveBeenCalled()
  })

  it('resends the code and shows a confirmation toast', async () => {
    mockResendOtp.mockResolvedValueOnce(undefined)
    renderVerifyWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() =>
      expect(
        screen.getByText('A new verification code has been sent.')
      ).toBeInTheDocument()
    )
    expect(mockResendOtp).toHaveBeenCalledWith('alex@prepwise.ai')
  })

  it('shows an error when resend fails', async () => {
    mockResendOtp.mockRejectedValueOnce(new Error('Failed to resend code.'))
    renderVerifyWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() => expect(screen.getByText('Failed to resend code.')).toBeInTheDocument())
  })

  it('falls back to a generic resend message when the rejection is not an Error', async () => {
    mockResendOtp.mockRejectedValueOnce('not an Error instance')
    renderVerifyWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() => expect(screen.getByText('Failed to resend code.')).toBeInTheDocument())
  })

  it('navigates to /signup when changing the email address', () => {
    renderVerify('?email=alex%40prepwise.ai')
    fireEvent.click(screen.getByText('Change email address'))
    expect(screen.getByText('Signup Page')).toBeInTheDocument()
  })

  it('does nothing on resend when there is no email to resend for', () => {
    renderVerifyWithResendReady()
    fireEvent.click(screen.getByText('Resend code now'))
    expect(mockResendOtp).not.toHaveBeenCalled()
  })
})
