import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { SignupPage } from './SignupPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockRegisterWithEmail, mockLoginWithGoogle } = vi.hoisted(() => ({
  mockRegisterWithEmail: vi.fn(),
  mockLoginWithGoogle: vi.fn(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    registerWithEmail: mockRegisterWithEmail,
    loginWithGoogle: mockLoginWithGoogle,
  }),
}))

vi.mock('../../components/ui/GoogleSignInButton', () => ({
  GoogleSignInButton: ({
    onSuccess,
    onError,
  }: {
    onSuccess: (credential: string) => void
    onError?: (err: string) => void
  }) => (
    <div>
      <button onClick={() => onSuccess('a-credential')}>MockGoogleSuccess</button>
      <button onClick={() => onError?.('Google exploded')}>MockGoogleError</button>
    </div>
  ),
}))

function renderSignup() {
  renderWithQueryClient(
    <MemoryRouter initialEntries={['/signup']}>
      <Routes>
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/verify-email" element={<div>Verify Email Page</div>} />
        <Route path="/setup" element={<div>Setup Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

function fillValidForm() {
  fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: 'Alex Chen' } })
  fireEvent.change(screen.getByLabelText(/Email address/i), {
    target: { value: 'alex@prepwise.ai' },
  })
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'Prepwise#2026' },
  })
}

describe('SignupPage', () => {
  beforeEach(() => {
    mockRegisterWithEmail.mockReset()
    mockLoginWithGoogle.mockReset()
  })

  it('keeps Create account disabled until the form is fully valid', () => {
    renderSignup()
    expect(screen.getByRole('button', { name: 'Create account' })).toBeDisabled()
    fillValidForm()
    expect(screen.getByRole('button', { name: 'Create account' })).not.toBeDisabled()
  })

  it('registers and navigates to /verify-email with the dev OTP in router state', async () => {
    mockRegisterWithEmail.mockResolvedValueOnce({
      email: 'alex@prepwise.ai',
      otp_sent: true,
      message: 'sent',
      dev_otp: '123456',
    })
    renderSignup()
    fillValidForm()
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => expect(screen.getByText('Verify Email Page')).toBeInTheDocument())
    expect(mockRegisterWithEmail).toHaveBeenCalledWith(
      'Alex Chen',
      'alex@prepwise.ai',
      'Prepwise#2026'
    )
  })

  it('registers and navigates with a null devOtp when the backend omits it', async () => {
    mockRegisterWithEmail.mockResolvedValueOnce({
      email: 'alex@prepwise.ai',
      otp_sent: true,
      message: 'sent',
    })
    renderSignup()
    fillValidForm()
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => expect(screen.getByText('Verify Email Page')).toBeInTheDocument())
  })

  it('shows the error message from a failed registration', async () => {
    mockRegisterWithEmail.mockRejectedValueOnce(
      new Error('An account with this email address already exists. Please sign in.')
    )
    renderSignup()
    fillValidForm()
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() =>
      expect(
        screen.getByText('An account with this email address already exists. Please sign in.')
      ).toBeInTheDocument()
    )
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockRegisterWithEmail.mockRejectedValueOnce('not an Error instance')
    renderSignup()
    fillValidForm()
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() =>
      expect(
        screen.getByText('Registration failed. Please try again.')
      ).toBeInTheDocument()
    )
  })

  it('shows a complete-all-fields error when force-submitted empty', () => {
    renderSignup()
    // Create account stays disabled with empty fields, so submit the
    // form directly to reach handleSubmit's own empty-fields check.
    fireEvent.submit(
      screen.getByRole('button', { name: 'Create account' }).closest('form')!
    )
    expect(screen.getByText('Please complete all fields.')).toBeInTheDocument()
    expect(mockRegisterWithEmail).not.toHaveBeenCalled()
  })

  it('shows a requirements error when force-submitted with a weak password', () => {
    renderSignup()
    fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: 'Alex Chen' } })
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'weak' } })
    // Create account stays disabled for a weak password, so submit the
    // form directly to reach handleSubmit's own requirements check.
    fireEvent.submit(
      screen.getByRole('button', { name: 'Create account' }).closest('form')!
    )
    expect(
      screen.getByText('Password does not meet all requirements.')
    ).toBeInTheDocument()
    expect(mockRegisterWithEmail).not.toHaveBeenCalled()
  })

  it('shows a field-level error for an incomplete email address', () => {
    renderSignup()
    fireEvent.change(screen.getByLabelText(/Full name/i), { target: { value: 'Alex Chen' } })
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.submit(
      screen.getByRole('button', { name: 'Create account' }).closest('form')!
    )
    expect(screen.getByText('Enter a complete email address.')).toBeInTheDocument()
    expect(mockRegisterWithEmail).not.toHaveBeenCalled()
  })

  it('shows the Error message when Google signup rejects with a real Error', async () => {
    mockLoginWithGoogle.mockRejectedValueOnce(new Error('Google account suspended.'))
    renderSignup()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() =>
      expect(screen.getByText('Google account suspended.')).toBeInTheDocument()
    )
  })

  it('shows a generic message when Google signup rejects with a non-Error', async () => {
    mockLoginWithGoogle.mockRejectedValueOnce('boom')
    renderSignup()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() =>
      expect(screen.getByText('Google authentication failed.')).toBeInTheDocument()
    )
  })

  it('signs up with Google and navigates to /setup', async () => {
    mockLoginWithGoogle.mockResolvedValueOnce(undefined)
    renderSignup()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() => expect(screen.getByText('Setup Page')).toBeInTheDocument())
  })

  it('shows an error when Google sign-in reports a failure', () => {
    renderSignup()
    fireEvent.click(screen.getByText('MockGoogleError'))
    expect(screen.getByText('Google exploded')).toBeInTheDocument()
  })
})
