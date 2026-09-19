import { createContext, useContext } from 'react'
import type {
  ForgotPasswordResponseData,
  RegisterResponseData,
  User,
} from '../types/auth'

export interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  loginWithGoogle: (credential: string) => Promise<User>
  registerWithEmail: (
    name: string,
    email: string,
    password: string
  ) => Promise<RegisterResponseData>
  verifyOtp: (email: string, otp: string) => Promise<User>
  resendOtp: (email: string) => Promise<void>
  loginWithEmail: (email: string, password: string) => Promise<User>
  forgotPassword: (email: string) => Promise<ForgotPasswordResponseData>
  verifyResetCode: (email: string, otp: string) => Promise<string>
  resetPassword: (resetToken: string, newPassword: string) => Promise<void>
  updatePreferredName: (preferredName: string) => Promise<User>
  deleteAccount: () => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
