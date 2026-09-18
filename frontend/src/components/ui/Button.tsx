
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'google' | 'secondary' | 'outline'
  isLoading?: boolean
  children: React.ReactNode
}

export function Button({
  variant = 'primary',
  isLoading = false,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyles =
    'w-full h-12 rounded-[10px] font-semibold text-[15px] flex items-center justify-center gap-2.5 transition-all duration-200 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed select-none'

  const variantStyles = {
    primary:
      'bg-navy text-white hover:bg-[#112d4e] active:scale-[0.99] shadow-sm',
    google:
      'bg-white text-ink border border-mist hover:bg-slate-50 hover:border-hairline active:scale-[0.99]',
    secondary:
      'bg-[#f4f7fa] text-ink border border-mist hover:bg-[#e2e8f0]',
    outline:
      'bg-transparent text-navy border border-navy hover:bg-navy/5',
  }[variant]

  return (
    <button
      className={`${baseStyles} ${variantStyles} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="inline-flex items-center gap-2">
          <svg
            className="animate-spin h-5 w-5 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Processing...</span>
        </span>
      ) : (
        children
      )}
    </button>
  )
}
