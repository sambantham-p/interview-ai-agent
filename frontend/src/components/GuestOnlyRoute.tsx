import { Navigate } from 'react-router'
import { useAuth } from '../lib/authContext'

interface GuestOnlyRouteProps {
  children: React.ReactNode
}


export function GuestOnlyRoute({ children }: GuestOnlyRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) return null
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return children
}
