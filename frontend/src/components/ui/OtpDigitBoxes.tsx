import {  useEffect, useRef, useState  } from 'react'

interface OtpDigitBoxesProps {
  value: string
  error?: boolean
  onChange: (val: string) => void
  onComplete?: (val: string) => void
  onResend?: () => void
  onChangeEmail?: () => void
  isResending?: boolean
}

export function OtpDigitBoxes({
  value,
  error = false,
  onChange,
  onComplete,
  onResend,
  onChangeEmail,
  isResending = false,
}: OtpDigitBoxesProps) {
  const [timer, setTimer] = useState(45)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // Split value into array of 6 characters
  const digits = Array.from({ length: 6 }, (_, i) => value[i] || '')

  // One interval for the component's lifetime, not one re-created every
  // tick - it keeps ticking harmlessly once timer hits 0, and a resend
  // click's setTimer(45) just gives it a new value to count down from.
  useEffect(() => {
    const interval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleDigitChange = (index: number, char: string) => {
    // Only accept numeric input
    if (char && !/^\d+$/.test(char)) return

    const newDigits = [...digits]
    newDigits[index] = char.slice(-1)
    const combined = newDigits.join('')
    onChange(combined)

    if (char && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }

    if (combined.length === 6 && onComplete) {
      onComplete(combined)
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text').trim()
    if (/^\d{6}$/.test(pastedData)) {
      onChange(pastedData)
      inputRefs.current[5]?.focus()
      if (onComplete) {
        onComplete(pastedData)
      }
    }
  }

  const handleResendClick = () => {
    if (timer === 0 && onResend) {
      onResend()
      setTimer(45)
    }
  }

  const formattedTimer = `00:${timer < 10 ? `0${timer}` : timer}`

  return (
    <div className="w-full flex flex-col items-center gap-5">
      <div
        role="group"
        aria-label="Verification code"
        className="flex items-center w-full max-w-90 gap-2"
        onPaste={handlePaste}
      >
        {digits.map((digit, i) => (
          <input
            key={i}
            ref={(el) => {
              inputRefs.current[i] = el
            }}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            value={digit}
            onChange={(e) => handleDigitChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            aria-label={`Digit ${i + 1} of 6`}
            autoFocus={i === 0}
            className={`flex-1 min-w-0 max-w-12.75 h-13.5 text-center text-[22px] font-bold text-ink bg-white rounded-lg border transition-all duration-150 focus:outline-none select-all ${
              error
                ? 'border-[#c43d4e]'
                : digit
                  ? 'border-brand bg-[#f8fafc]'
                  : 'border-mist focus:border-brand focus:ring-2 focus:ring-brand/20'
            }`}
          />
        ))}
      </div>

      {/* Resend & Change email footer from Figma node 7:551 - stacked and
          centered, matching the design (not spread into a row) */}
      <div className="flex flex-col items-center w-full max-w-90 text-[13px] text-muted gap-2 pt-1">
        <div>
          {timer > 0 ? (
            <span>Resend code in {formattedTimer}</span>
          ) : (
            <button
              type="button"
              onClick={handleResendClick}
              disabled={isResending}
              className="text-brand font-semibold hover:underline cursor-pointer"
            >
              {isResending ? 'Sending...' : 'Resend code now'}
            </button>
          )}
        </div>

        {onChangeEmail && (
          <button
            type="button"
            onClick={onChangeEmail}
            className="text-navy hover:underline cursor-pointer"
          >
            Change email address
          </button>
        )}
      </div>
    </div>
  )
}
