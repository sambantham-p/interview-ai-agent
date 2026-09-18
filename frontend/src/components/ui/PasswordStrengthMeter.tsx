import { checkPasswordStrength } from '../../lib/passwordRules'

interface PasswordStrengthMeterProps {
  password?: string
}

export function PasswordStrengthMeter({ password = '' }: PasswordStrengthMeterProps) {
  const { hasMinLength, hasUpperLower, hasNumber, hasSpecial, passedCount } =
    checkPasswordStrength(password)

  const getStrengthLabel = () => {
    if (!password) return { label: 'Enter password', color: 'text-faint' }
    if (passedCount <= 1) return { label: 'Weak password', color: 'text-[#c43d4e]' }
    if (passedCount <= 2) return { label: 'Fair password', color: 'text-[#d48a16]' }
    if (passedCount === 3) return { label: 'Good password', color: 'text-teal-600' }
    return { label: 'Strong password', color: 'text-brand' }
  }

  const { label, color } = getStrengthLabel()

  
  const segmentColors = [
    '#c43d4e',
    '#d48a16',
    'var(--color-brand)',
    'var(--color-brand)',
  ]

  return (
    <div className="w-full flex flex-col gap-2.5 mt-1 select-none">
      {/* 4-Segment Bar from Figma node 7:499 */}
      <div className="flex items-center gap-1.5 w-full">
        {[1, 2, 3, 4].map((segment) => {
          const isFilled = passedCount >= segment
          return (
            <div
              key={segment}
              className="h-1 flex-1 rounded-full transition-all duration-200"
              style={{
                backgroundColor: isFilled ? segmentColors[segment - 1] : 'var(--color-mist)',
              }}
            />
          )
        })}
      </div>

      {/* Strength Label */}
      <div className="flex items-center justify-between">
        <span className={`text-[12px] font-medium ${color}`}>{label}</span>
      </div>

      {/* 4 Requirements Checklist from Figma node 7:505 */}
      <div className="grid grid-cols-2 gap-y-1.5 gap-x-2 text-[11px] text-muted">
        <div
          className={`flex items-center gap-1.5 ${hasMinLength ? 'text-brand font-medium' : ''}`}
          aria-label={`8+ characters requirement ${hasMinLength ? 'met' : 'not met'}`}
        >
          <span aria-hidden="true">{hasMinLength ? '✓' : '○'}</span>
          <span>8+ characters</span>
        </div>
        <div
          className={`flex items-center gap-1.5 ${hasUpperLower ? 'text-brand font-medium' : ''}`}
          aria-label={`Uppercase and lowercase requirement ${hasUpperLower ? 'met' : 'not met'}`}
        >
          <span aria-hidden="true">{hasUpperLower ? '✓' : '○'}</span>
          <span>Uppercase & lowercase</span>
        </div>
        <div
          className={`flex items-center gap-1.5 ${hasNumber ? 'text-brand font-medium' : ''}`}
          aria-label={`A number requirement ${hasNumber ? 'met' : 'not met'}`}
        >
          <span aria-hidden="true">{hasNumber ? '✓' : '○'}</span>
          <span>A number</span>
        </div>
        <div
          className={`flex items-center gap-1.5 ${hasSpecial ? 'text-brand font-medium' : ''}`}
          aria-label={`A special character requirement ${hasSpecial ? 'met' : 'not met'}`}
        >
          <span aria-hidden="true">{hasSpecial ? '✓' : '○'}</span>
          <span>A special character</span>
        </div>
      </div>
    </div>
  )
}
