import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { PasswordStrengthMeter } from '../../components/ui/PasswordStrengthMeter'
import { GoogleSignInButton } from '../../components/ui/GoogleSignInButton'
import { useAuth } from '../../lib/authContext'
import { checkPasswordStrength } from '../../lib/passwordRules'
import { isValidEmail } from '../../lib/emailRules'
import { toErrorMessage } from '../../lib/errorMessage'
import type { RegisterResponseData, User } from '../../types/auth'

export function SignupPage() {
  const navigate = useNavigate()
  const { loginWithGoogle, registerWithEmail } = useAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  const { isValid: meetsRequirements } = checkPasswordStrength(password)
  const canSubmit = Boolean(name && email && meetsRequirements)

  const registerMutation = useMutation<
    RegisterResponseData,
    Error,
    { name: string; email: string; password: string }
  >({
    mutationFn: ({ name, email, password }) =>
      registerWithEmail(name, email, password).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Registration failed. Please try again.'))
      }),
    onSuccess: (_result, variables) => {
      navigate(`/verify-email?email=${encodeURIComponent(variables.email)}`)
    },
  })

  const googleLoginMutation = useMutation<User, Error, string>({
    mutationFn: (credential) =>
      loginWithGoogle(credential).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Google authentication failed.'))
      }),
    onSuccess: () => navigate('/setup'),
  })

  const isSubmitting = registerMutation.isPending || googleLoginMutation.isPending
  const error =
    validationError ?? registerMutation.error?.message ?? googleLoginMutation.error?.message ?? null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !email || !password) {
      setValidationError('Please complete all fields.')
      return
    }
    if (!isValidEmail(email)) {
      setEmailError('Enter a complete email address.')
      return
    }
    if (!meetsRequirements) {
      setValidationError('Password does not meet all requirements.')
      return
    }

    setEmailError(null)
    setValidationError(null)
    registerMutation.mutate({ name, email, password })
  }

  const handleGoogleSuccess = (credential: string) => {
    setValidationError(null)
    googleLoginMutation.mutate(credential)
  }

  return (
    <AuthLayout>
      <div className="w-full flex flex-col gap-6">
        {/* Heading  */}
        <div className="flex flex-col gap-1.5">
          <h2
            className="text-[28px] font-bold text-ink tracking-tight"
          >
            Create your account
          </h2>
          <p className="text-[14px] text-muted leading-normal">
            Build a private practice space tailored to your next role.
          </p>
        </div>

        <ErrorAlert message={error} />

        {/* Google Sign In */}
        <GoogleSignInButton
          onSuccess={handleGoogleSuccess}
          onError={(err) => setValidationError(err)}
          isLoading={isSubmitting}
        />

        {/* Divider */}
        <div className="flex items-center gap-3 select-none">
          <div className="flex-1 h-px bg-mist" />
          <span className="text-[11px] font-semibold text-faint">OR</span>
          <div className="flex-1 h-px bg-mist" />
        </div>

        {/* Registration Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Full name"
            placeholder="Your full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="name"
          />

          <Input
            label="Email address"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              setEmailError(null)
            }}
            error={emailError ?? undefined}
            required
            autoComplete="email"
          />

          <div>
            <Input
              label="Password"
              isPassword
              placeholder="Prepwise#2026"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
            {/* Password Strength Section  */}
            <PasswordStrengthMeter password={password} />
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              disabled={!canSubmit}
            >
              Create account
            </Button>
          </div>
        </form>

        {/* Account Link */}
        <div className="flex items-center justify-center gap-1.5 text-[14px] text-muted pt-1">
          <span>Already have an account?</span>
          <Link
            to="/login"
            className="font-semibold text-navy hover:underline cursor-pointer"
          >
            Sign in
          </Link>
        </div>
      </div>
    </AuthLayout>
  )
}
