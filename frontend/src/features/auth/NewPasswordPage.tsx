import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { SuccessCard } from '../../components/ui/SuccessCard'
import { useAuth } from '../../lib/authContext'
import { checkPasswordStrength } from '../../lib/passwordRules'
import { toErrorMessage } from '../../lib/errorMessage'

export function NewPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { resetPassword } = useAuth()

  // Read from the URL, not router state, so the token survives a page
  // refresh on this route instead of being lost.
  const resetToken = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  const { isValid: meetsRequirements } = checkPasswordStrength(password)
  const passwordsMatch = password.length > 0 && password === confirmPassword
  const ready = meetsRequirements && passwordsMatch

  const resetPasswordMutation = useMutation<void, Error, { token: string; password: string }>({
    mutationFn: ({ token, password }) =>
      resetPassword(token, password).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Something went wrong. Please try again.'))
      }),
  })

  const error = validationError ?? resetPasswordMutation.error?.message ?? null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!resetToken) {
      setValidationError('Your reset session has expired. Please start over.')
      return
    }
    if (!meetsRequirements) {
      setValidationError('Password does not meet all requirements.')
      return
    }
    if (!passwordsMatch) {
      setValidationError('Passwords do not match.')
      return
    }

    setValidationError(null)
    resetPasswordMutation.mutate({ token: resetToken, password })
  }

  if (resetPasswordMutation.isSuccess) {
    return (
      <AuthLayout>
        <SuccessCard
          title="Password updated"
          message="You can now sign in with your new password."
          ctaLabel="Return to sign in"
          onCta={() => navigate('/login')}
        />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <div className="w-full flex flex-col gap-6">
        {/* Heading from Figma (Node 7:640) */}
        <div className="flex flex-col gap-2">
          <span
            className="text-[12px] font-bold tracking-wider text-brand uppercase"
          >
            Final step
          </span>
          <h2
            className="text-[28px] font-bold text-ink tracking-tight"
          >
            Choose a new password
          </h2>
          <p className="text-[14px] text-muted leading-normal">
            Use a unique password you haven&apos;t used for Prepwise before.
          </p>
        </div>

        <ErrorAlert message={error} />

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <Input
            label="New password"
            isPassword
            placeholder="Enter a new password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />

          <Input
            label="Confirm new password"
            isPassword
            placeholder="Re-enter your new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />

          {/* Password status from Figma (Node 7:654) */}
          {(password || confirmPassword) && (
            <div
              className={`flex items-start gap-2 p-3 rounded-md text-[12px] ${
                ready ? 'bg-[#ddf6f1] text-ink' : 'bg-slate-50 text-muted'
              }`}
            >
              <span aria-hidden="true" className={ready ? 'text-brand' : 'text-faint'}>
                {ready ? '✓' : '○'}
              </span>
              <span>
                {ready
                  ? 'Passwords match and meet all requirements'
                  : !meetsRequirements
                    ? 'Password must be 8+ characters with upper/lowercase, a number, and a special character.'
                    : 'Passwords do not match yet.'}
              </span>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            isLoading={resetPasswordMutation.isPending}
            disabled={!ready}
          >
            Update password
          </Button>
        </form>

        {/* Footer note from Figma (Node 7:659) */}
        <p className="text-[12px] text-muted text-center">
          You&apos;ll be signed out of other sessions.
        </p>
      </div>
    </AuthLayout>
  )
}
