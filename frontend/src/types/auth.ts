export interface User {
  id: string
  email: string
  name: string
  picture: string | null
  auth_provider: 'google' | 'email'
  is_verified: boolean
  created_at: string
}

export interface AuthResponseData {
  user: User
  token?: string
}

export interface RegisterResponseData {
  email: string
  otp_sent: boolean
  message: string
  dev_otp?: string
}

export interface ForgotPasswordResponseData {
  message: string
  dev_otp?: string
}

export interface VerifyResetCodeResponseData {
  reset_token: string
}

export interface ResetPasswordResponseData {
  message: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}
