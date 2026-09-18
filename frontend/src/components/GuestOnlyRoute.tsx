import { Navigate } from 'react-router'
import { useAuth } from '../lib/authContext'

interface GuestOnlyRouteProps {
  children: React.ReactNode
}

// Wraps auth-only pages (login, signup, forgot/reset password, OTP
// verification) so an already-signed-in visitor is bounced to the home
// page instead of seeing a login form again. Waits out isLoading first -
// that's AuthProvider's one-time localStorage hydration on mount, and
// redirecting (or rendering the form) before it resolves would act on a
// stale "not authenticated yet" reading.
export function GuestOnlyRoute({ children }: GuestOnlyRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null
  if (isAuthenticated) return <Navigate to="/" replace />

  return children
}
