import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { queryClient } from '../app/queryClient'
import { api, AUTH_TOKEN_STORAGE_KEY, setUnauthorizedHandler } from './api'
import type {
  AuthResponseData,
  ForgotPasswordResponseData,
  RegisterResponseData,
  ResetPasswordResponseData,
  User,
  UserResponseData,
  VerifyResetCodeResponseData,
} from '../types/auth'

interface AuthContextType {
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

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const STORAGE_USER_KEY = 'prepwise_user'


function isStoredUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as Record<string, unknown>).id === 'string' &&
    typeof (value as Record<string, unknown>).email === 'string'
  )
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    try {
      const storedUser = localStorage.getItem(STORAGE_USER_KEY)
      const storedToken = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
      if (storedUser && storedToken) {
        const parsed: unknown = JSON.parse(storedUser)
        if (isStoredUser(parsed)) {
          setUser(parsed)
          setToken(storedToken)
        } else {
          localStorage.removeItem(STORAGE_USER_KEY)
          localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
        }
      } else {
        localStorage.removeItem(STORAGE_USER_KEY)
        localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
      }
    } catch {
      // Corrupted localStorage data - clear it so it doesn't keep failing.
      localStorage.removeItem(STORAGE_USER_KEY)
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const saveAuthSession = (authData: AuthResponseData) => {
    setUser(authData.user)
    if (authData.token) {
      setToken(authData.token)
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, authData.token)
    }
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(authData.user))
  }

// Shared response shape for Google, OTP, and password sign-in.
// Keeps session persistence in one place without changing the auth
// hydration loading state; each page uses its mutation state for loading.
  const authenticate = async (path: string, payload: unknown): Promise<User> => {
    const data = await api.post<AuthResponseData>(path, payload)
    saveAuthSession(data)
    return data.user
  }

  const loginWithGoogle = (credential: string): Promise<User> =>
    authenticate('/auth/google', { credential })

  const verifyOtp = (email: string, otp: string): Promise<User> =>
    authenticate('/auth/verify-otp', { email, otp })

  const loginWithEmail = (email: string, password: string): Promise<User> =>
    authenticate('/auth/login', { email, password })

  const registerWithEmail = (
    name: string,
    email: string,
    password: string
  ): Promise<RegisterResponseData> =>
    api.post<RegisterResponseData>('/auth/register', { name, email, password })

  const resendOtp = async (email: string): Promise<void> => {
    await api.post('/auth/resend-otp', { email })
  }

  const forgotPassword = (email: string): Promise<ForgotPasswordResponseData> =>
    api.post<ForgotPasswordResponseData>('/auth/forgot-password', { email })

  const verifyResetCode = async (email: string, otp: string): Promise<string> => {
    const data = await api.post<VerifyResetCodeResponseData>('/auth/verify-reset-code', {
      email,
      otp,
    })
    return data.reset_token
  }

  const resetPassword = async (resetToken: string, newPassword: string): Promise<void> => {
    await api.post<ResetPasswordResponseData>('/auth/reset-password', {
      reset_token: resetToken,
      new_password: newPassword,
    })
  }

  const updatePreferredName = async (preferredName: string): Promise<User> => {
    const data = await api.patch<UserResponseData>('/auth/me', {
      preferred_name: preferredName,
    })
    setUser(data.user)
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(data.user))
    return data.user
  }

  const deleteAccount = async (): Promise<void> => {
    await api.delete('/auth/me')
    logout()
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(STORAGE_USER_KEY)
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
    queryClient.clear()
  }

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [])

  const value = useMemo<AuthContextType>(
    () => ({
      user,
      token,
      isAuthenticated: !!user && !!token,
      isLoading,
      loginWithGoogle,
      registerWithEmail,
      verifyOtp,
      resendOtp,
      loginWithEmail,
      forgotPassword,
      verifyResetCode,
      resetPassword,
      updatePreferredName,
      deleteAccount,
      logout,
    }),
    [user, token, isLoading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>

}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
