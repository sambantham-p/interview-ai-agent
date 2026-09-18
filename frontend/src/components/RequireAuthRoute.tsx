import { Navigate } from 'react-router'
import { useAuth } from '../lib/authContext'

interface RequireAuthRouteProps {
  children: React.ReactNode
}

// Protects feature pages that require a signed-in user.
// Waits for AuthProvider to finish localStorage hydration before redirecting,
// preventing valid users from being redirected on a hard refresh.
export function RequireAuthRoute({ children }: RequireAuthRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null
  if (!isAuthenticated) return <Navigate to="/" replace />

  return children
}
