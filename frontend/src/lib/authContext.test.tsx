import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider, useAuth } from './authContext'
import { AUTH_TOKEN_STORAGE_KEY } from './api'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('./api', async () => {
  const actual = await vi.importActual<typeof import('./api')>('./api')
  return {
    ...actual,
    api: { get: mockGet, post: mockPost },
  }
})

const fakeUser = {
  id: 'usr_1',
  email: 'alex@prepwise.ai',
  name: 'Alex',
  picture: null,
  auth_provider: 'email' as const,
  is_verified: true,
  created_at: '2026-01-01T00:00:00Z',
}

function Probe({ onReady }: { onReady: (ctx: ReturnType<typeof useAuth>) => void }) {
  const ctx = useAuth()
  onReady(ctx)
  return (
    <div>
      <span data-testid="loading">{String(ctx.isLoading)}</span>
      <span data-testid="authed">{String(ctx.isAuthenticated)}</span>
      <span data-testid="user-email">{ctx.user?.email ?? 'none'}</span>
    </div>
  )
}

function renderWithProbe() {
  let latest: ReturnType<typeof useAuth> | undefined
  render(
    <AuthProvider>
      <Probe
        onReady={(ctx) => {
          latest = ctx
        }}
      />
    </AuthProvider>
  )
  return {
    get ctx() {
      return latest as ReturnType<typeof useAuth>
    },
  }
}

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    mockGet.mockReset()
    mockPost.mockReset()
  })

  it('throws when useAuth is used outside an AuthProvider', () => {
    const Bare = () => {
      useAuth()
      return null
    }
    expect(() => render(<Bare />)).toThrow('useAuth must be used within an AuthProvider')
  })

  it('starts loading, then settles to unauthenticated with no stored session', async () => {
    renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    expect(screen.getByTestId('authed').textContent).toBe('false')
  })

  it('restores a previously stored user and token from localStorage', async () => {
    localStorage.setItem('prepwise_user', JSON.stringify(fakeUser))
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'stored-token')

    renderWithProbe()

    await waitFor(() => expect(screen.getByTestId('authed').textContent).toBe('true'))
    expect(screen.getByTestId('user-email').textContent).toBe('alex@prepwise.ai')
  })

  it('ignores corrupted localStorage data instead of crashing', async () => {
    localStorage.setItem('prepwise_user', '{not valid json')

    renderWithProbe()

    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    expect(screen.getByTestId('authed').textContent).toBe('false')
    expect(localStorage.getItem('prepwise_user')).toBeNull()
  })

  it('clears a validly-parsed but wrong-shaped stored user instead of trusting it', async () => {
    localStorage.setItem('prepwise_user', JSON.stringify({ not: 'a real user' }))

    renderWithProbe()

    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    expect(screen.getByTestId('authed').textContent).toBe('false')
    expect(localStorage.getItem('prepwise_user')).toBeNull()
  })

  it('loginWithEmail persists the session on success', async () => {
    mockPost.mockResolvedValueOnce({ user: fakeUser, token: 'new-token' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.loginWithEmail('alex@prepwise.ai', 'Prepwise#2026')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/login', {
      email: 'alex@prepwise.ai',
      password: 'Prepwise#2026',
    })
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBe('new-token')
    expect(screen.getByTestId('authed').textContent).toBe('true')
  })

  it('a sign-in response without a token does not count as signed in', async () => {
    mockPost.mockResolvedValueOnce({ user: fakeUser })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.loginWithEmail('alex@prepwise.ai', 'Prepwise#2026')
    })

    expect(screen.getByTestId('authed').textContent).toBe('false')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('loginWithEmail propagates a rejection without persisting a session', async () => {
    mockPost.mockRejectedValueOnce(new Error('Invalid email or password.'))
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await expect(
      act(async () => {
        await probe.ctx.loginWithEmail('alex@prepwise.ai', 'wrong')
      })
    ).rejects.toThrow('Invalid email or password.')

    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull()
  })

  it('loginWithGoogle sends the credential payload', async () => {
    mockPost.mockResolvedValueOnce({ user: fakeUser, token: 'g-token' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.loginWithGoogle('a-real-id-token')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/google', {
      credential: 'a-real-id-token',
    })
  })

  it('registerWithEmail returns the response without establishing a session', async () => {
    mockPost.mockResolvedValueOnce({
      email: 'new@prepwise.ai',
      otp_sent: true,
      message: 'sent',
      dev_otp: '123456',
    })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    let result: { dev_otp?: string } | undefined
    await act(async () => {
      result = await probe.ctx.registerWithEmail('New User', 'new@prepwise.ai', 'Prepwise#2026')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/register', {
      name: 'New User',
      email: 'new@prepwise.ai',
      password: 'Prepwise#2026',
    })
    expect(result?.dev_otp).toBe('123456')
    expect(screen.getByTestId('authed').textContent).toBe('false')
  })

  it('verifyOtp establishes a session on success', async () => {
    mockPost.mockResolvedValueOnce({ user: fakeUser, token: 'verified-token' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.verifyOtp('alex@prepwise.ai', '123456')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/verify-otp', {
      email: 'alex@prepwise.ai',
      otp: '123456',
    })
    expect(screen.getByTestId('authed').textContent).toBe('true')
  })

  it('resendOtp calls the resend endpoint', async () => {
    mockPost.mockResolvedValueOnce({})
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.resendOtp('alex@prepwise.ai')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/resend-otp', { email: 'alex@prepwise.ai' })
  })

  it('forgotPassword returns the response data', async () => {
    mockPost.mockResolvedValueOnce({ message: 'sent', dev_otp: '654321' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    let result: { dev_otp?: string } | undefined
    await act(async () => {
      result = await probe.ctx.forgotPassword('alex@prepwise.ai')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/forgot-password', {
      email: 'alex@prepwise.ai',
    })
    expect(result?.dev_otp).toBe('654321')
  })

  it('verifyResetCode returns the reset token', async () => {
    mockPost.mockResolvedValueOnce({ reset_token: 'reset-abc' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    let token: string | undefined
    await act(async () => {
      token = await probe.ctx.verifyResetCode('alex@prepwise.ai', '654321')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/verify-reset-code', {
      email: 'alex@prepwise.ai',
      otp: '654321',
    })
    expect(token).toBe('reset-abc')
  })

  it('resetPassword calls the reset endpoint with the token and new password', async () => {
    mockPost.mockResolvedValueOnce({ message: 'updated' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.resetPassword('reset-abc', 'NewPrepwise#2026')
    })

    expect(mockPost).toHaveBeenCalledWith('/auth/reset-password', {
      reset_token: 'reset-abc',
      new_password: 'NewPrepwise#2026',
    })
  })

  it('keeps isLoading false while a login request is in flight (guards the blank-page fix)', async () => {
    let resolvePost: (value: { user: typeof fakeUser; token: string }) => void
    mockPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve
      })
    )
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    // GuestOnlyRoute/RequireAuthRoute both render nothing while isLoading
    // is true, so if a future change reintroduces setIsLoading(true) here,
    // the sign-in page would go blank for the whole request - this is the
    // regression this test exists to catch.
    let pending!: Promise<unknown>
    act(() => {
      pending = probe.ctx.loginWithGoogle('a-real-id-token')
    })
    expect(screen.getByTestId('loading').textContent).toBe('false')

    await act(async () => {
      resolvePost({ user: fakeUser, token: 'g-token' })
      await pending
    })
    expect(screen.getByTestId('loading').textContent).toBe('false')
    expect(screen.getByTestId('authed').textContent).toBe('true')
  })

  it('keeps isLoading false while a registration request is in flight (guards the blank-page fix)', async () => {
    let resolvePost: (value: { email: string; otp_sent: boolean; message: string }) => void
    mockPost.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve
      })
    )
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    let pending!: Promise<unknown>
    act(() => {
      pending = probe.ctx.registerWithEmail('New User', 'new@prepwise.ai', 'Prepwise#2026')
    })
    expect(screen.getByTestId('loading').textContent).toBe('false')

    await act(async () => {
      resolvePost({ email: 'new@prepwise.ai', otp_sent: true, message: 'sent' })
      await pending
    })
    expect(screen.getByTestId('loading').textContent).toBe('false')
  })

  it('logout clears the session from state and localStorage', async () => {
    mockPost.mockResolvedValueOnce({ user: fakeUser, token: 'a-token' })
    const probe = renderWithProbe()
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      await probe.ctx.loginWithEmail('alex@prepwise.ai', 'Prepwise#2026')
    })
    expect(screen.getByTestId('authed').textContent).toBe('true')

    act(() => {
      probe.ctx.logout()
    })

    expect(screen.getByTestId('authed').textContent).toBe('false')
    expect(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem('prepwise_user')).toBeNull()
  })
})
