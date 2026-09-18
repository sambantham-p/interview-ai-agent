import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockForgotPassword } = vi.hoisted(() => ({
  mockForgotPassword: vi.fn(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    forgotPassword: mockForgotPassword,
  }),
}))

function renderForgot() {
  renderWithQueryClient(
    <MemoryRouter initialEntries={['/forgot-password']}>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password/verify" element={<div>Reset Verify Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    mockForgotPassword.mockReset()
  })

  it('shows a validation error when submitting with no email', () => {
    renderForgot()
    fireEvent.submit(screen.getByRole('button', { name: 'Send reset code' }).closest('form')!)
    expect(screen.getByText('Please enter your email address.')).toBeInTheDocument()
    expect(mockForgotPassword).not.toHaveBeenCalled()
  })

  it('shows a field-level error for an incomplete email address', () => {
    renderForgot()
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset code' }))
    expect(screen.getByText('Enter a complete email address.')).toBeInTheDocument()
    expect(mockForgotPassword).not.toHaveBeenCalled()
  })

  it('submits and navigates to the reset-verify page with the dev OTP in state', async () => {
    mockForgotPassword.mockResolvedValueOnce({ message: 'sent', dev_otp: '112233' })
    renderForgot()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset code' }))

    await waitFor(() => expect(screen.getByText('Reset Verify Page')).toBeInTheDocument())
    expect(mockForgotPassword).toHaveBeenCalledWith('alex@prepwise.ai')
  })

  it('navigates with a null devOtp when the backend omits it', async () => {
    mockForgotPassword.mockResolvedValueOnce({ message: 'sent' })
    renderForgot()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset code' }))

    await waitFor(() => expect(screen.getByText('Reset Verify Page')).toBeInTheDocument())
  })

  it('shows the error message from a failed request', async () => {
    mockForgotPassword.mockRejectedValueOnce(new Error('Something broke.'))
    renderForgot()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset code' }))

    await waitFor(() => expect(screen.getByText('Something broke.')).toBeInTheDocument())
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockForgotPassword.mockRejectedValueOnce('not an Error instance')
    renderForgot()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset code' }))

    await waitFor(() =>
      expect(
        screen.getByText('Something went wrong. Please try again.')
      ).toBeInTheDocument()
    )
  })
})
