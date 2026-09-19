import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { OtpVerificationForm } from '../../components/ui/OtpVerificationForm'
import { SuccessCard } from '../../components/ui/SuccessCard'
import { useAuth } from '../../lib/authContext'
import { toErrorMessage } from '../../lib/errorMessage'
import { useToast } from '../../lib/toastContext'
import type { User } from '../../types/auth'

export function VerifyOtpPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { verifyOtp, resendOtp } = useAuth()
  const { showToast } = useToast()

  const email = searchParams.get('email') || ''

  const [otp, setOtp] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isResending, setIsResending] = useState(false)

  const verifyMutation = useMutation<User, Error, string>({
    mutationFn: (code) =>
      verifyOtp(email, code).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Invalid verification code.'))
      }),
  })

  const error = validationError ?? verifyMutation.error?.message ?? null

  const handleVerify = (codeToVerify?: string) => {
    const code = codeToVerify || otp
    if (code.length !== 6) {
      setValidationError('Please enter the full 6-digit verification code.')
      return
    }
    if (!email) {
      setValidationError('Missing email address. Please sign up again.')
      return
    }

    setValidationError(null)
    verifyMutation.mutate(code)
  }

  if (verifyMutation.isSuccess) {
    return (
      <AuthLayout>
        <SuccessCard
          title="Email verified"
          message="Your account is ready."
          ctaLabel="Continue to Prepwise"
          onCta={() => navigate('/setup')}
        />
      </AuthLayout>
    )
  }

  const handleResend = async () => {
    if (!email) return
    setIsResending(true)
    setValidationError(null)
    try {
      await resendOtp(email)
      showToast('A new verification code has been sent.')
    } catch (err: unknown) {
      showToast(toErrorMessage(err, 'Failed to resend code.'), 'error')
    } finally {
      setIsResending(false)
    }
  }

  return (
    <AuthLayout>
      <OtpVerificationForm
        eyebrow="Verify your email"
        heading="Check your inbox"
        description={
          <>
            We sent a 6-digit code to{' '}
            <strong className="text-ink font-semibold">{email || 'your email'}</strong>. Enter it
            below to secure your account.
          </>
        }
        error={error}
        otp={otp}
        onOtpChange={(val) => {
          setOtp(val)
          setValidationError(null)
        }}
        onOtpComplete={(val) => handleVerify(val)}
        onResend={handleResend}
        onChangeEmail={() => navigate('/signup')}
        isResending={isResending}
        isVerifying={verifyMutation.isPending}
        onSubmit={() => handleVerify()}
        submitLabel="Verify email"
      />
    </AuthLayout>
  )
}
