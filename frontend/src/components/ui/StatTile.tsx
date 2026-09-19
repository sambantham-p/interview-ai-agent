import { Card } from './Card'

type StatTone = 'brand' | 'navy' | 'success'

interface StatTileProps {
  icon: React.ReactNode
  label: string
  value: string | number
  tone?: StatTone
}

const TONE_STYLES: Record<StatTone, string> = {
  brand: 'bg-brand/10 text-brand',
  navy: 'bg-navy/10 text-navy',
  success: 'bg-emerald-50 text-emerald-600',
}

export function StatTile({ icon, label, value, tone = 'brand' }: StatTileProps) {
  return (
    <Card className="flex items-center gap-4">
      <div
        className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${TONE_STYLES[tone]}`}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-ink leading-tight">{value}</p>
        <p className="text-xs text-muted mt-0.5">{label}</p>
      </div>
    </Card>
  )
}
