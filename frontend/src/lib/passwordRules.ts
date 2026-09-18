// Provides shared password strength validation for signup and password reset.
export interface PasswordCheck {
  hasMinLength: boolean
  hasUpperLower: boolean
  hasNumber: boolean
  hasSpecial: boolean
  passedCount: number
  isValid: boolean
}

export function checkPasswordStrength(password: string): PasswordCheck {
  const hasMinLength = password.length >= 8
  const hasUpperLower = /[A-Z]/.test(password) && /[a-z]/.test(password)
  const hasNumber = /\d/.test(password)
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?/~`]/.test(password)
  const passedCount = [hasMinLength, hasUpperLower, hasNumber, hasSpecial].filter(
    Boolean
  ).length

  return {
    hasMinLength,
    hasUpperLower,
    hasNumber,
    hasSpecial,
    passedCount,
    isValid: passedCount === 4,
  }
}
