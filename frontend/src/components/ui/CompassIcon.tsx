export function CompassIcon({ className = 'w-6 h-6' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="12" cy="12" r="9.5" stroke="var(--color-brand)" strokeWidth="1.2" />
      <path
        d="M15.5 8.5L13.2 13.2L8.5 15.5L10.8 10.8L15.5 8.5Z"
        stroke="var(--color-brand)"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  )
}
