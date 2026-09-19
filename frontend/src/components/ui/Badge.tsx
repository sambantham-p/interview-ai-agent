type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'brand' | 'navy'

interface BadgeProps {
  tone?: BadgeTone
  children: React.ReactNode
  className?: string
}


const TONE_STYLES: Record<BadgeTone, string> = {
  neutral: 'bg-[#f4f7fa] text-muted border border-mist',
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200',
  danger: 'bg-red-50 text-red-700 border border-red-200',
  brand: 'bg-brand/10 text-[#0d6b5f] border border-brand/30',
  navy: 'bg-navy/10 text-navy border border-navy/20',
}

export function Badge({ tone = 'neutral', children, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${TONE_STYLES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
