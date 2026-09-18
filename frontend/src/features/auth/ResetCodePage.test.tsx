import { screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { ResetCodePage } from './ResetCodePage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockVerifyResetCode, mockForgotPassword } = vi.hoisted(() => ({
  mockVerifyResetCode: vi.fn(),
  mockForgotPassword: vi.fn(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    verifyResetCode: mockVerifyResetCode,
    forgotPassword: mockForgotPassword,
  }),
}))

function renderReset(search = '', state?: unknown) {
  renderWithQueryClient(
    <MemoryRouter initialEntries={[{ pathname: '/reset-password/verify', search, state }]}>
      <Routes>
        <Route path="/reset-password/verify" element={<ResetCodePage />} />
        <Route path="/reset-password/new" element={<div>New Password Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

// See VerifyOtpPage.test.tsx for why fake timers must be active before
// mount and switched back to real before any `waitFor`.
function renderResetWithResendReady(search = '', state?: unknown) {
  vi.useFakeTimers()
  renderReset(search, state)
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

describe('ResetCodePage', () => {
  beforeEach(() => {
    mockVerifyResetCode.mockReset()
    mockForgotPassword.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the auto-filled dev OTP banner when devOtp arrives via router state', () => {
    renderReset('', { devOtp: '112233' })
    expect(screen.getByText(/Dev code auto-filled/)).toBeInTheDocument()
    expect(screen.getByText('112233')).toBeInTheDocument()
  })

  it('verifies the code, shows the success state, then navigates with the reset token in the URL', async () => {
    mockVerifyResetCode.mockResolvedValueOnce('a-reset-token')
    renderReset('?email=alex%40prepwise.ai')

    enterOtp('123456')

    await waitFor(() => expect(screen.getByText('Code verified')).toBeInTheDocument())
    expect(mockVerifyResetCode).toHaveBeenCalledWith('alex@prepwise.ai', '123456')

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(screen.getByText('New Password Page')).toBeInTheDocument()
  })

  it('shows the error message from a failed verification', async () => {
    mockVerifyResetCode.mockRejectedValueOnce(new Error('Invalid or expired reset code.'))
    renderReset('?email=alex%40prepwise.ai')

    enterOtp('123456')

    await waitFor(() =>
      expect(screen.getByText('Invalid or expired reset code.')).toBeInTheDocument()
    )
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockVerifyResetCode.mockRejectedValueOnce('not an Error instance')
    renderReset('?email=alex%40prepwise.ai')

    enterOtp('123456')

    await waitFor(() =>
      expect(screen.getByText('Invalid or expired reset code.')).toBeInTheDocument()
    )
  })

  it('shows a missing-email error when no email is present', async () => {
    renderReset()
    enterOtp('123456')

    await waitFor(() =>
      expect(screen.getByText('Missing email address. Please start over.')).toBeInTheDocument()
    )
    expect(mockVerifyResetCode).not.toHaveBeenCalled()
  })

  it('resends via forgotPassword once the timer allows it', async () => {
    mockForgotPassword.mockResolvedValueOnce({ message: 'sent' })
    renderResetWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() => expect(mockForgotPassword).toHaveBeenCalledWith('alex@prepwise.ai'))
  })

  it('shows an error when resend fails', async () => {
    mockForgotPassword.mockRejectedValueOnce(new Error('Failed to resend code.'))
    renderResetWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() => expect(screen.getByText('Failed to resend code.')).toBeInTheDocument())
  })

  it('falls back to a generic resend message when the rejection is not an Error', async () => {
    mockForgotPassword.mockRejectedValueOnce('not an Error instance')
    renderResetWithResendReady('?email=alex%40prepwise.ai')

    fireEvent.click(screen.getByText('Resend code now'))

    await waitFor(() => expect(screen.getByText('Failed to resend code.')).toBeInTheDocument())
  })

  it('verifies immediately when clicking the dev-banner Continue now button', async () => {
    mockVerifyResetCode.mockResolvedValueOnce('a-reset-token')
    renderReset('?email=alex%40prepwise.ai', { devOtp: '112233' })

    fireEvent.click(screen.getByText('Continue now'))

    await waitFor(() => expect(screen.getByText('Code verified')).toBeInTheDocument())
    expect(mockVerifyResetCode).toHaveBeenCalledWith('alex@prepwise.ai', '112233')
  })

  it('keeps Continue disabled for an incomplete code', () => {
    renderReset('?email=alex%40prepwise.ai')
    enterOtp('12')
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })

  it('shows an incomplete-code error when the dev banner supplies a short code', async () => {
    renderReset('?email=alex%40prepwise.ai', { devOtp: '123' })
    fireEvent.click(screen.getByText('Continue now'))

    await waitFor(() =>
      expect(screen.getByText('Please enter the full 6-digit code.')).toBeInTheDocument()
    )
    expect(mockVerifyResetCode).not.toHaveBeenCalled()
  })

  it('does nothing on resend when there is no email to resend for', () => {
    renderResetWithResendReady()
    fireEvent.click(screen.getByText('Resend code now'))
    expect(mockForgotPassword).not.toHaveBeenCalled()
  })
})
