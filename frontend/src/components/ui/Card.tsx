interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  interactive?: boolean
}


export function Card({
  children,
  className = '',
  interactive = false,
  ...props
}: CardProps) {
  const interactiveStyles = interactive
    ? 'transition-all duration-200 hover:shadow-[0_8px_24px_-12px_rgba(10,23,48,0.18)] hover:border-hairline hover:-translate-y-0.5'
    : ''
  return (
    <div
      className={`rounded-2xl bg-white border border-mist p-5 sm:p-6 ${interactiveStyles} ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
