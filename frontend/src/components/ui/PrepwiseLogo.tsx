interface PrepwiseLogoProps {
  variant?: 'light' | 'dark'
  size?: 'sm' | 'md' | 'lg'
  showWordmark?: boolean
  className?: string
}

export function PrepwiseLogo({
  variant = 'dark',
  size = 'md',
  showWordmark = true,
  className = '',
}: PrepwiseLogoProps) {
  const markDimensions = {
    sm: 'w-9 h-8',
    md: 'w-11 h-10',
    lg: 'w-13 h-12',
  }[size]

  const wordmarkSize = {
    sm: 'text-[22px]',
    md: 'text-[26px]',
    lg: 'text-[32px]',
  }[size]

  const textColor = variant === 'light' ? 'text-ink' : 'text-white'

  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`}>
      {/* Brand mark from Figma: message-circle-check */}
      <div
        className={`${markDimensions} rounded-xl bg-linear-to-br from-[#2bc9b4] to-[#0f8f80] flex items-center justify-center p-1.5 shadow-[0_6px_16px_-6px_rgba(24,169,153,0.75)]`}
        aria-hidden="true"
      >
        <svg
          viewBox="0 0 21 21"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          <path
            d="M7.80975 10.4999L9.60223 12.2926L13.1872 8.70724M2.42528 14.3916C2.55706 14.7241 2.5864 15.0883 2.50952 15.4376L1.55502 18.3866C1.52427 18.5362 1.53222 18.6911 1.57813 18.8367C1.62403 18.9823 1.70637 19.1138 1.81733 19.2187C1.92828 19.3235 2.06419 19.3983 2.21215 19.4359C2.36011 19.4735 2.51522 19.4727 2.66278 19.4335L5.72166 18.539C6.05122 18.4736 6.39252 18.5022 6.70663 18.6214C8.62046 19.5153 10.7885 19.7044 12.8281 19.1554C14.8678 18.6064 16.648 17.3546 17.8547 15.6208C19.0615 13.887 19.6171 11.7827 19.4237 9.6791C19.2303 7.5755 18.3002 5.60783 16.7975 4.12323C15.2948 2.63864 13.3162 1.73254 11.2106 1.5648C9.10503 1.39705 7.00789 1.97845 5.28917 3.2064C3.57045 4.43435 2.34061 6.22995 1.81663 8.2764C1.29265 10.3228 1.50821 12.4886 2.42528 14.3916Z"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {showWordmark && (
        <span
          aria-label="Prepwise"
          className={`font-display font-extrabold leading-none tracking-[-0.045em] ${wordmarkSize} ${textColor}`}
        >
          Prep
          <span className="bg-linear-to-r from-brand to-[#5eead4] bg-clip-text text-transparent">
            wise
          </span>
        </span>
      )}
    </div>
  )
}
