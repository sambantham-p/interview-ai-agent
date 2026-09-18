import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { AuthLayout } from './AuthLayout'
import { OtpVerificationForm } from '../../components/ui/OtpVerificationForm'
import { SuccessCard } from '../../components/ui/SuccessCard'
import { useAuth } from '../../lib/authContext'
import { PASSWORD_RESET_EXPIRY_MINUTES } from '../../lib/authConstants'
import { toErrorMessage } from '../../lib/errorMessage'

function readDevOtp(state: unknown): string {
  if (typeof state !== 'object' || state === null || !('devOtp' in state)) return ''
  const devOtp = (state as { devOtp?: unknown }).devOtp
  return typeof devOtp === 'string' ? devOtp : ''
}

export function ResetCodePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { verifyResetCode, forgotPassword } = useAuth()

  const email = searchParams.get('email') || ''
  const devOtp = readDevOtp(location.state)

  const [otp, setOtp] = useState(devOtp || '')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isResending, setIsResending] = useState(false)

  const verifyResetCodeMutation = useMutation<string, Error, string>({
    mutationFn: (code) =>
      verifyResetCode(email, code).catch((err: unknown) => {
        throw new Error(toErrorMessage(err, 'Invalid or expired reset code.'))
      }),
  })

  const error = validationError ?? verifyResetCodeMutation.error?.message ?? null

  const handleContinue = (codeToVerify?: string) => {
    const code = codeToVerify || otp
    if (code.length !== 6) {
      setValidationError('Please enter the full 6-digit code.')
      return
    }
    if (!email) {
      setValidationError('Missing email address. Please start over.')
      return
    }

    setValidationError(null)
    verifyResetCodeMutation.mutate(code)
  }

  const resetToken = verifyResetCodeMutation.data

  if (resetToken) {
    return (
      <AuthLayout>
        <SuccessCard
          title="Code verified"
          message="Your code checked out. Choose a new password to finish resetting your account."
          ctaLabel="Continue"
          onCta={() =>
            navigate(`/reset-password/new?token=${encodeURIComponent(resetToken)}`)
          }
        />
      </AuthLayout>
    )
  }

  const handleResend = async () => {
    if (!email) return
    setIsResending(true)
    setValidationError(null)
    try {
      await forgotPassword(email)
    } catch (err: unknown) {
      setValidationError(toErrorMessage(err, 'Failed to resend code.'))
    } finally {
      setIsResending(false)
    }
  }

  return (
    <AuthLayout>
      <OtpVerificationForm
        eyebrow="Email sent"
        heading="Reset code on its way"
        description={
          <>
            If an account exists for{' '}
            <strong className="text-ink font-semibold">{email || 'that email'}</strong>,
            you&apos;ll receive a 6-digit code shortly.
          </>
        }
        extraContent={
         
          <div className="bg-[#ddf6f1] flex flex-col gap-2 p-5 rounded-[10px]">
            <p aria-hidden="true" className="text-brand text-[24px] leading-none">
              ✓
            </p>
            <p className="text-ink text-[14px] font-medium">Check your inbox</p>
            <p className="text-muted text-[13px] leading-relaxed">
              The code expires in {PASSWORD_RESET_EXPIRY_MINUTES} minutes.
            </p>
          </div>
        }
        devOtp={devOtp}
        devOtpButtonLabel="Continue now"
        onDevOtpClick={() => handleContinue(devOtp)}
        error={error}
        otp={otp}
        onOtpChange={(val) => {
          setOtp(val)
          setValidationError(null)
        }}
        onOtpComplete={(val) => handleContinue(val)}
        onResend={handleResend}
        isResending={isResending}
        isVerifying={verifyResetCodeMutation.isPending}
        onSubmit={() => handleContinue()}
        submitLabel="Continue"
      />
    </AuthLayout>
  )
}
