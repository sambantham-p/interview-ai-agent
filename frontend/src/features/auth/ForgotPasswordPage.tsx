import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { ErrorAlert } from '../../components/ui/ErrorAlert'
import { useAuth } from '../../lib/authContext'
import { isValidEmail } from '../../lib/emailRules'
import { toErrorMessage } from '../../lib/errorMessage'
import type { ForgotPasswordResponseData } from '../../types/auth'

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { forgotPassword } = useAuth()

  const [email, setEmail] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)

  const forgotPasswordMutation = useMutation<ForgotPasswordResponseData, Error, string>({
    mutationFn: (email) =>
      forgotPassword(email).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Something went wrong. Please try again.'))
      }),
    onSuccess: (result) => {
      navigate(`/reset-password/verify?email=${encodeURIComponent(email)}`, {
        state: { devOtp: result.dev_otp ?? null },
      })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) {
      setEmailError('Please enter your email address.')
      return
    }
    if (!isValidEmail(email)) {
      setEmailError('Enter a complete email address.')
      return
    }

    setEmailError(null)
    forgotPasswordMutation.mutate(email)
  }

  return (
    <AuthLayout>
      <div className="w-full flex flex-col gap-6">
        {/* Heading from Figma (Node 7:571) */}
        <div className="flex flex-col gap-2">
          <span
            className="text-[12px] font-bold tracking-wider text-brand uppercase"
          >
            Password reset
          </span>
          <h2
            className="text-[28px] font-bold text-ink tracking-tight"
          >
            Reset your password
          </h2>
          <p className="text-[14px] text-muted leading-normal">
            Enter the email linked to your account and we&apos;ll send a secure reset code.
          </p>
        </div>

        <ErrorAlert message={forgotPasswordMutation.error?.message ?? null} />

        {/* Field + Button from Figma (Node 7:575, 7:579) */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
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

          <Button type="submit" variant="primary" isLoading={forgotPasswordMutation.isPending}>
            Send reset code
          </Button>
        </form>

        {/* Back link from Figma (Node 7:581) */}
        <Link
          to="/login"
          className="text-[13px] font-semibold text-navy text-center hover:underline cursor-pointer"
        >
          ← Back to sign in
        </Link>
      </div>
    </AuthLayout>
  )
}
