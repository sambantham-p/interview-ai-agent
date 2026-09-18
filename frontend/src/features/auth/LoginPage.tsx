import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { GoogleSignInButton } from '../../components/ui/GoogleSignInButton'
import { useAuth } from '../../lib/authContext'
import { isValidEmail } from '../../lib/emailRules'
import { toErrorMessage } from '../../lib/errorMessage'
import type { User } from '../../types/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const { loginWithGoogle, loginWithEmail } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  // Only for errors that never touch the network (empty fields, or the
  // GoogleSignInButton reporting a render/init failure) - a real
  // submission failure lives in the relevant mutation's own `error`.
  const [validationError, setValidationError] = useState<string | null>(null)

  const emailLoginMutation = useMutation<User, Error, { email: string; password: string }>({
    mutationFn: ({ email, password }) =>
      loginWithEmail(email, password).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Invalid email or password.'))
      }),
    onSuccess: () => navigate('/setup'),
  })

  const googleLoginMutation = useMutation<User, Error, string>({
    mutationFn: (credential) =>
      loginWithGoogle(credential).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Google authentication failed.'))
      }),
    onSuccess: () => navigate('/setup'),
  })

  const isSubmitting = emailLoginMutation.isPending || googleLoginMutation.isPending
  const error =
    validationError ?? emailLoginMutation.error?.message ?? googleLoginMutation.error?.message ?? null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      setValidationError('Please fill in both email and password.')
      return
    }
    if (!isValidEmail(email)) {
      setEmailError('Enter a complete email address.')
      return
    }

    setEmailError(null)
    setValidationError(null)
    emailLoginMutation.mutate({ email, password })
  }

  const handleGoogleSuccess = (credential: string) => {
    setValidationError(null)
    googleLoginMutation.mutate(credential)
  }

  return (
    <AuthLayout>
      <div className="w-full flex flex-col gap-6">
        {/* Heading from Figma (Node 7:431) */}
        <div className="flex flex-col gap-1.5">
          <h2
            className="text-[28px] font-bold text-ink tracking-tight"
          >
            Welcome back
          </h2>
          <p className="text-[14px] text-muted leading-normal">
            Sign in to continue your interview preparation.
          </p>
        </div>

        <ErrorAlert message={error} />

       
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
            autoComplete="username"
          />

          <div>
            <Input
              label="Password"
              isPassword
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <div className="flex justify-end mt-1.5">
              <Link
                to="/forgot-password"
                className="text-[12px] text-muted hover:text-navy cursor-pointer"
              >
                Forgot password?
              </Link>
            </div>
          </div>

          <div className="pt-2">
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Sign in
            </Button>
          </div>
        </form>

        {/* Divider from Figma (Node 7:447) */}
        <div className="flex items-center gap-3 select-none">
          <div className="flex-1 h-px bg-mist" />
          <span className="text-[11px] font-semibold text-faint">OR</span>
          <div className="flex-1 h-px bg-mist" />
        </div>

        {/* Google Sign In from Figma (Node 7:451) */}
        <GoogleSignInButton
          onSuccess={handleGoogleSuccess}
          onError={(err) => setValidationError(err)}
          isLoading={isSubmitting}
        />

        {/* Account Link from Figma (Node 7:454) */}
        <div className="flex items-center justify-center gap-1.5 text-[14px] text-muted pt-1">
          <span>New to Prepwise?</span>
          <Link
            to="/signup"
            className="font-semibold text-navy hover:underline cursor-pointer"
          >
            Create an account
          </Link>
        </div>
      </div>
    </AuthLayout>
  )
}
