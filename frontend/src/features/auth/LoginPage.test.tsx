import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { LoginPage } from './LoginPage'
import { renderWithQueryClient } from '../../test/renderWithQueryClient'

const { mockLoginWithEmail, mockLoginWithGoogle } = vi.hoisted(() => ({
  mockLoginWithEmail: vi.fn<(...args: unknown[]) => unknown>(),
  mockLoginWithGoogle: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('../../lib/authContext', () => ({
  useAuth: () => ({
    loginWithEmail: mockLoginWithEmail,
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

function renderLogin(initialEntries: Parameters<typeof MemoryRouter>[0]['initialEntries'] = ['/login']) {
  renderWithQueryClient(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/setup" element={<div>Setup Page</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockLoginWithEmail.mockReset()
    mockLoginWithGoogle.mockReset()
  })

  it('shows a validation error when submitting with empty fields', () => {
    renderLogin()
    // fireEvent.click would be blocked by jsdom's own `required` validation
    // before React ever sees it - submitting the form directly reaches the
    // handler's own empty-fields branch instead.
    fireEvent.submit(screen.getByRole('button', { name: 'Sign in' }).closest('form')!)
    expect(
      screen.getByText('Please fill in both email and password.')
    ).toBeInTheDocument()
    expect(mockLoginWithEmail).not.toHaveBeenCalled()
  })

  it('logs in and navigates to /setup on success', async () => {
    mockLoginWithEmail.mockResolvedValueOnce(undefined)
    renderLogin()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.change(screen.getByLabelText(/^Password$/i), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(screen.getByText('Setup Page')).toBeInTheDocument())
    expect(mockLoginWithEmail).toHaveBeenCalledWith('alex@prepwise.ai', 'Prepwise#2026')
  })

  it('shows the error message from a failed login', async () => {
    mockLoginWithEmail.mockRejectedValueOnce(new Error('Invalid email or password.'))
    renderLogin()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.change(screen.getByLabelText(/^Password$/i), {
      target: { value: 'wrong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() =>
      expect(screen.getByText('Invalid email or password.')).toBeInTheDocument()
    )
  })

  it('falls back to a generic message when the rejection is not an Error', async () => {
    mockLoginWithEmail.mockRejectedValueOnce('not an Error instance')
    renderLogin()

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise.ai' },
    })
    fireEvent.change(screen.getByLabelText(/^Password$/i), {
      target: { value: 'wrong-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() =>
      expect(screen.getByText('Invalid email or password.')).toBeInTheDocument()
    )
  })

  it('shows a field-level error for an incomplete email address', async () => {
    renderLogin()
    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: 'alex@prepwise' },
    })
    fireEvent.change(screen.getByLabelText(/^Password$/i), {
      target: { value: 'Prepwise#2026' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByText('Enter a complete email address.')).toBeInTheDocument()
    expect(mockLoginWithEmail).not.toHaveBeenCalled()
  })

  it('signs in with Google and navigates to /setup', async () => {
    mockLoginWithGoogle.mockResolvedValueOnce(undefined)
    renderLogin()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() => expect(screen.getByText('Setup Page')).toBeInTheDocument())
    expect(mockLoginWithGoogle).toHaveBeenCalledWith('a-credential')
  })

  it('shows an error when Google sign-in reports a failure', () => {
    renderLogin()
    fireEvent.click(screen.getByText('MockGoogleError'))
    expect(screen.getByText('Google exploded')).toBeInTheDocument()
  })

  it('shows the Error message when Google login rejects with a real Error', async () => {
    mockLoginWithGoogle.mockRejectedValueOnce(new Error('Google account suspended.'))
    renderLogin()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() =>
      expect(screen.getByText('Google account suspended.')).toBeInTheDocument()
    )
  })

  it('shows a generic message when Google login rejects with a non-Error', async () => {
    mockLoginWithGoogle.mockRejectedValueOnce('boom')
    renderLogin()

    fireEvent.click(screen.getByText('MockGoogleSuccess'))

    await waitFor(() =>
      expect(screen.getByText('Google authentication failed.')).toBeInTheDocument()
    )
  })
})
