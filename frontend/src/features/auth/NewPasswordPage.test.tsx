import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { NewPasswordPage } from './NewPasswordPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockResetPassword } = vi.hoisted(() => ({
  mockResetPassword: vi.fn(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    resetPassword: mockResetPassword,
    logout: vi.fn(),
  }),
}))

function renderNewPassword(token?: string) {
  const search = token ? `?token=${encodeURIComponent(token)}` : ''
  renderWithQueryClient(
    <MemoryRouter initialEntries={[`/reset-password/new${search}`]}>
      <Routes>
        <Route path="/reset-password/new" element={<NewPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

function fillMatchingPasswords(password = 'Prepwise#2026') {
  fireEvent.change(screen.getByLabelText(/^New password/i), { target: { value: password } })
  fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
    target: { value: password },
  })
}

describe('NewPasswordPage', () => {
  beforeEach(() => {
    mockResetPassword.mockReset()
  })

  it('keeps Update password disabled until both fields are valid and match', () => {
    renderNewPassword('a-token')
    const submit = screen.getByRole('button', { name: 'Update password' })
    expect(submit).toBeDisabled()

    fillMatchingPasswords()
    expect(submit).not.toBeDisabled()
  })

  it('shows a mismatch message while the confirmation differs', () => {
    renderNewPassword('a-token')
    fireEvent.change(screen.getByLabelText(/^New password/i), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: 'Different#2026' },
    })
    expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
  })

  it('shows the strength meter while the password is weak', () => {
    renderNewPassword('a-token')
    fireEvent.change(screen.getByLabelText(/^New password/i), { target: { value: 'weak' } })
    expect(screen.getByText('Weak password')).toBeInTheDocument()
  })

  it('resets the password, shows the success state, then navigates to /login', async () => {
    mockResetPassword.mockResolvedValueOnce(undefined)
    renderNewPassword('a-token')

    fillMatchingPasswords()
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }))

    await waitFor(() => expect(screen.getByText('Password updated')).toBeInTheDocument())
    expect(mockResetPassword).toHaveBeenCalledWith('a-token', 'Prepwise#2026')

    fireEvent.click(screen.getByRole('button', { name: 'Return to sign in' }))
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('shows the error message from a failed reset', async () => {
    mockResetPassword.mockRejectedValueOnce(new Error('Invalid or expired reset token.'))
    renderNewPassword('a-token')

    fillMatchingPasswords()
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }))

    await waitFor(() =>
      expect(screen.getByText('Invalid or expired reset token.')).toBeInTheDocument()
    )
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockResetPassword.mockRejectedValueOnce('not an Error instance')
    renderNewPassword('a-token')

    fillMatchingPasswords()
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }))

    await waitFor(() =>
      expect(
        screen.getByText('Something went wrong. Please try again.')
      ).toBeInTheDocument()
    )
  })

  it('shows a requirements error when the form is force-submitted with a weak password', () => {
    renderNewPassword('a-token')
    // Update password stays disabled for a weak password, so submit the
    // form directly to reach handleSubmit's own requirements check.
    fireEvent.change(screen.getByLabelText(/^New password/i), { target: { value: 'weak' } })
    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: 'weak' },
    })
    fireEvent.submit(
      screen.getByRole('button', { name: 'Update password' }).closest('form')!
    )
    expect(
      screen.getByText('Password does not meet all requirements.')
    ).toBeInTheDocument()
    expect(mockResetPassword).not.toHaveBeenCalled()
  })

  it('shows a mismatch error when the form is force-submitted with non-matching strong passwords', () => {
    renderNewPassword('a-token')
    fireEvent.change(screen.getByLabelText(/^New password/i), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.change(screen.getByLabelText(/Confirm new password/i), {
      target: { value: 'Prepwise#2027' },
    })
    fireEvent.submit(
      screen.getByRole('button', { name: 'Update password' }).closest('form')!
    )
    expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
    expect(mockResetPassword).not.toHaveBeenCalled()
  })

  it('shows an expired-session error when submitted with no reset token', () => {
    renderNewPassword()
    // The button stays disabled without a valid+matching password, so
    // submit the form directly to reach the handler's own token check.
    fillMatchingPasswords()
    fireEvent.submit(
      screen.getByRole('button', { name: 'Update password' }).closest('form')!
    )
    expect(
      screen.getByText('Your reset session has expired. Please start over.')
    ).toBeInTheDocument()
    expect(mockResetPassword).not.toHaveBeenCalled()
  })
})
