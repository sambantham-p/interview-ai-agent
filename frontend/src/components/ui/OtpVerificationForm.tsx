import type { ReactNode } from 'react'
import { Button } from './Button'
import { ErrorAlert } from './ErrorAlert'
import { OtpDigitBoxes } from './OtpDigitBoxes'

interface OtpVerificationFormProps {
  eyebrow: string
  heading: string
  description: ReactNode
  extraContent?: ReactNode
  error: string | null
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


export function OtpVerificationForm({
  eyebrow,
  heading,
  description,
  extraContent,
  error,
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

      <ErrorAlert message={error} />

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
