import { Navigate } from 'react-router'
import { useAuth } from '../lib/authContext'

interface GuestOnlyRouteProps {
  children: React.ReactNode
}

// Redirects signed-in users away from auth pages to resume setup.
// Waits for AuthProvider loading to finish before checking authentication.
export function GuestOnlyRoute({ children }: GuestOnlyRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null
  if (isAuthenticated) return <Navigate to="/setup" replace />

  return children
}
