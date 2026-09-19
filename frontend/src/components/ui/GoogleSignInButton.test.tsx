import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { GoogleSignInButton } from './GoogleSignInButton'

afterEach(() => {
  delete (window as unknown as { google?: unknown }).google
  vi.restoreAllMocks()
  vi.useRealTimers()
})

type GoogleIdInitialize = NonNullable<Window['google']>['accounts']['id']['initialize']
type GoogleIdRenderButton = NonNullable<Window['google']>['accounts']['id']['renderButton']

function mockGoogleId(
  overrides: Partial<{
    initialize: GoogleIdInitialize
    renderButton: GoogleIdRenderButton
  }> = {}
) {
  const initialize = vi.fn<GoogleIdInitialize>(
    overrides.initialize ?? ((config) => config)
  )
  const renderButton = vi.fn<GoogleIdRenderButton>(overrides.renderButton ?? (() => {}))
  window.google = { accounts: { id: { initialize, renderButton } } }
  return { initialize, renderButton }
}

// The component polls for window.google to become available (the GIS
// script tag loads async/defer, so it may not be ready the instant the
// effect first runs) before giving up after a 3s timeout and showing the
// fallback button. Tests exercising that fallback need fake timers active
// before mount, advanced past that timeout, then switched back to real
// timers before any assertion/interaction.
function renderAndReachFallback(props: Parameters<typeof GoogleSignInButton>[0]) {
  vi.useFakeTimers()
  render(<GoogleSignInButton {...props} />)
  act(() => {
    vi.advanceTimersByTime(3000)
  })
  vi.useRealTimers()
}

describe('GoogleSignInButton', () => {
  it('renders the fallback button when Google Identity Services is unavailable', () => {
    renderAndReachFallback({ onSuccess: vi.fn<(...args: unknown[]) => unknown>() })
    expect(screen.getByText('Continue with Google')).toBeInTheDocument()
  })

  it('is disabled while isLoading is true, in the fallback state', () => {
    renderAndReachFallback({ onSuccess: vi.fn<(...args: unknown[]) => unknown>(), isLoading: true })
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('initializes Google Identity Services and renders its real button instead of the fallback', () => {
    const { initialize, renderButton } = mockGoogleId()

    render(<GoogleSignInButton onSuccess={vi.fn<(...args: unknown[]) => unknown>()} />)

    expect(initialize).toHaveBeenCalled()
    // jsdom always reports offsetWidth 0, so the 360 fallback width is used.
    expect(renderButton).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({ type: 'standard', width: 360 })
    )
    // The fallback button is only rendered when Google's real button
    // couldn't be - it must not exist once renderButton succeeds.
    expect(screen.queryByText('Continue with Google')).not.toBeInTheDocument()
  })

  it('renders the real button once Google becomes available shortly after mount', () => {
    // Reproduces the actual race this component guards against: the GIS
    // script (loaded async/defer) isn't ready on the very first effect
    // run, but becomes ready moments later.
    vi.useFakeTimers()
    const renderButton = vi.fn<(...args: unknown[]) => unknown>()
    const initialize = vi.fn<
      (config: { callback: (res: { credential: string }) => void }) => unknown
    >((config) => config)

    render(<GoogleSignInButton onSuccess={vi.fn<(...args: unknown[]) => unknown>()} />)
    expect(renderButton).not.toHaveBeenCalled()

    window.google = { accounts: { id: { initialize, renderButton } } }
    act(() => {
      vi.advanceTimersByTime(100)
    })

    expect(renderButton).toHaveBeenCalled()
    vi.useRealTimers()
    expect(screen.queryByText('Continue with Google')).not.toBeInTheDocument()
  })

  it('forwards a returned credential to onSuccess via the initialize callback', () => {
    const onSuccess = vi.fn<(...args: unknown[]) => unknown>()
    let capturedCallback: ((res: { credential: string }) => void) | undefined
    mockGoogleId({
      initialize: (config: { callback: (res: { credential: string }) => void }) => {
        capturedCallback = config.callback
      },
    })

    render(<GoogleSignInButton onSuccess={onSuccess} />)

    capturedCallback?.({ credential: 'real-credential' })
    expect(onSuccess).toHaveBeenCalledWith('real-credential')
  })

  it('calls onError when the initialize callback returns no credential', () => {
    const onError = vi.fn<(...args: unknown[]) => unknown>()
    let capturedCallback: ((res: { credential: string }) => void) | undefined
    mockGoogleId({
      initialize: (config: { callback: (res: { credential: string }) => void }) => {
        capturedCallback = config.callback
      },
    })

    render(<GoogleSignInButton onSuccess={vi.fn<(...args: unknown[]) => unknown>()} onError={onError} />)

    capturedCallback?.({ credential: '' })
    expect(onError).toHaveBeenCalledWith('No credential returned from Google.')
  })

  it('logs an error and never initializes when VITE_GOOGLE_CLIENT_ID is unset', () => {
    // .env sets a real VITE_GOOGLE_CLIENT_ID for every other test in this
    // file - this is the one place that exercises the missing-client-id
    // branch. A fake fallback client id used to be used here instead of
    // failing loudly - see CLAUDE.md's Frontend Conventions for why that
    // was removed.
    const original = import.meta.env.VITE_GOOGLE_CLIENT_ID
    // import.meta.env's values are typed `any` (Vite's default
    // ImportMetaEnv), so overriding one here for the test needs no cast.
    import.meta.env.VITE_GOOGLE_CLIENT_ID = ''
    const { initialize } = mockGoogleId()
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    try {
      render(<GoogleSignInButton onSuccess={vi.fn<(...args: unknown[]) => unknown>()} />)
      expect(initialize).not.toHaveBeenCalled()
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'VITE_GOOGLE_CLIENT_ID is not set - Google Sign-In cannot be initialized.'
      )
    } finally {
      import.meta.env.VITE_GOOGLE_CLIENT_ID = original
    }
  })

  it('calls onError, not onSuccess, when the fallback button is clicked', () => {
    const onError = vi.fn<(...args: unknown[]) => unknown>()
    const onSuccess = vi.fn<(...args: unknown[]) => unknown>()

    renderAndReachFallback({ onSuccess, onError })
    fireEvent.click(screen.getByRole('button'))

    expect(onSuccess).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledWith(
      'Google sign-in is unavailable right now. Please try again.'
    )
  })
})
