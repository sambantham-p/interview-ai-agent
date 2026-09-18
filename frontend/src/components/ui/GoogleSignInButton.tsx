import { useEffect, useRef, useState } from 'react'
import { GoogleIcon } from './GoogleIcon'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (res: { credential: string }) => void }) => void
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
        }
      }
    }
  }
}

interface GoogleSignInButtonProps {
  onSuccess: (credential: string) => void
  onError?: (err: string) => void
  isLoading?: boolean
}

// Uses Google's official Sign-In button via Google Identity Services.
// No custom or invisible button overlay; styling is limited to Google's
// supported options (theme, shape, and size).
export function GoogleSignInButton({
  onSuccess,
  onError,
  isLoading = false,
}: GoogleSignInButtonProps) {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  const containerRef = useRef<HTMLDivElement>(null)
  const [renderFailed, setRenderFailed] = useState(false)

  useEffect(() => {
    if (!clientId) {
      // A fake fallback client id would render a button that silently
      // fails against Google's real endpoint - failing loudly in the
      // console for whoever forgot to set VITE_GOOGLE_CLIENT_ID is more
      // useful than a button that looks like it should work.
      console.error(
        'VITE_GOOGLE_CLIENT_ID is not set - Google Sign-In cannot be initialized.'
      )
      return
    }

    let cancelled = false

    const renderRealButton = () => {
      if (cancelled || !window.google?.accounts?.id || !containerRef.current) return false
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response: { credential: string }) => {
            if (response.credential) {
              onSuccess(response.credential)
            } else {
              onError?.('No credential returned from Google.')
            }
          },
        })
        window.google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          shape: 'rectangular',
          text: 'continue_with',
          width: containerRef.current.offsetWidth || 360,
        })
        return true
      } catch {
        return false
      }
    }

    if (renderRealButton()) return

     // The GIS script tag (index.html) loads with async/defer, so it can
    // still be mid-flight when this effect first runs on mount - a single
    // check-once here would wrongly and permanently fall back to the
    // dev-only button just because of that race, even though the script
    // (and a real client id) both work fine moments later. Poll briefly
    // for window.google to become available before giving up for real.
    const pollId = window.setInterval(() => {
      if (renderRealButton()) {
        window.clearInterval(pollId)
      }
    }, 100)
    const timeoutId = window.setTimeout(() => {
      window.clearInterval(pollId)
      if (!cancelled) setRenderFailed(true)
    }, 3000)

    return () => {
      cancelled = true
      window.clearInterval(pollId)
      window.clearTimeout(timeoutId)
    }
  }, [clientId, onSuccess, onError])

  const handleFallbackClick = () => {
    onError?.('Google sign-in is unavailable right now. Please try again.')
  }

  return (
    <div className="w-full flex flex-col items-center">
      <div
        ref={containerRef}
        className={`w-full flex justify-center ${renderFailed ? 'hidden' : ''} ${
          isLoading ? 'opacity-60 pointer-events-none' : ''
        }`}
      />

      {renderFailed && (
        <button
          type="button"
          onClick={handleFallbackClick}
          disabled={isLoading}
          className="w-full h-12 rounded-[10px] bg-white border border-mist text-ink font-semibold text-[15px] flex items-center justify-center gap-3 hover:bg-slate-50 hover:border-hairline active:scale-[0.99] transition-all cursor-pointer shadow-xs disabled:opacity-60 select-none"
        >
          <GoogleIcon className="w-5 h-5" />
          <span>Continue with Google</span>
        </button>
      )}
    </div>
  )
}
