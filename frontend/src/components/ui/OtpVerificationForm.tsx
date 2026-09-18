import type { ReactNode } from 'react'
import { Button } from './Button'
import { ErrorAlert } from './ErrorAlert'
import { OtpDigitBoxes } from './OtpDigitBoxes'

interface OtpVerificationFormProps {
  eyebrow: string
  heading: string
  description: ReactNode
  extraContent?: ReactNode
  devOtp: string
  devOtpButtonLabel: string
  onDevOtpClick: () => void
  error: string | null
  resendNotice?: string | null
  otp: string
  onOtpChange: (val: string) => void
  onOtpComplete: (val: string) => void
  onResend: () => void
  onChangeEmail?: () => void
  isResending: boolean
  isVerifying: boolean
  onSubmit: () => void
  submitLabel: string
}

// Shared by VerifyOtpPage (signup email verification) and ResetCodePage
// (password reset) - both flows are "enter a 6-digit code, optionally
// resend it, then continue," just with different copy and what happens
// after the code checks out (each page keeps its own mutation/success
// screen, only the input form itself is shared here).
export function OtpVerificationForm({
  eyebrow,
  heading,
  description,
  extraContent,
  devOtp,
  devOtpButtonLabel,
  onDevOtpClick,
  error,
  resendNotice,
  otp,
  onOtpChange,
  onOtpComplete,
  onResend,
  onChangeEmail,
  isResending,
  isVerifying,
  onSubmit,
  submitLabel,
}: OtpVerificationFormProps) {
  return (
    <div className="w-full flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-semibold tracking-wider text-brand uppercase">
          {eyebrow}
        </span>
        <h2 className="text-[28px] font-bold text-ink tracking-tight">{heading}</h2>
        <p className="text-[14px] text-muted leading-normal">{description}</p>
      </div>

      {extraContent}

      {devOtp && (
        <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 text-[13px] rounded-[10px] flex items-center justify-between">
          <span>
            Dev code auto-filled: <strong>{devOtp}</strong>
          </span>
          <button
            type="button"
            onClick={onDevOtpClick}
            className="font-semibold text-brand underline cursor-pointer"
          >
            {devOtpButtonLabel}
          </button>
        </div>
      )}

      <ErrorAlert message={error} />
      {resendNotice && (
        <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-[13px] rounded-[10px]">
          {resendNotice}
        </div>
      )}

      <div className="py-2">
        <OtpDigitBoxes
          value={otp}
          error={Boolean(error)}
          onChange={onOtpChange}
          onComplete={onOtpComplete}
          onResend={onResend}
          onChangeEmail={onChangeEmail}
          isResending={isResending}
        />
      </div>

      <div className="pt-2">
        <Button
          type="button"
          variant="primary"
          onClick={onSubmit}
          isLoading={isVerifying}
          disabled={otp.length !== 6}
        >
          {submitLabel}
        </Button>
      </div>
    </div>
  )
}
