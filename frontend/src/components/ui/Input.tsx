import {  useState  } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  isPassword?: boolean
}

export function Input({
  label,
  error,
  isPassword = false,
  type = 'text',
  className = '',
  id,
  ...props
}: InputProps) {
  const [showPassword, setShowPassword] = useState(false)
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)

  const resolvedType = isPassword ? (showPassword ? 'text' : 'password') : type

  return (
    <div className="w-full flex flex-col gap-1.5 text-left">
      {label && (
        <label
          htmlFor={inputId}
          className="text-[14px] font-semibold text-ink"
        >
          {label}
        </label>
      )}

      <div className="relative w-full">
        <input
          id={inputId}
          type={resolvedType}
          className={`w-full h-12 px-3.5 rounded-[10px] bg-white border ${
            error ? 'border-red-400 focus:border-red-500' : 'border-mist focus:border-brand'
          } text-[15px] text-ink placeholder-faint focus:outline-none focus:ring-2 focus:ring-brand/20 transition-all duration-150 ${
            isPassword ? 'pr-16' : ''
          } ${className}`}
          {...props}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            aria-pressed={showPassword}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[13px] font-medium text-muted hover:text-ink transition-colors cursor-pointer select-none"
          >
            {showPassword ? 'Hide' : 'Show'}
          </button>
        )}
      </div>

      {error && <p className="text-[12px] text-red-600 mt-0.5">{error}</p>}
    </div>
  )
}
