import { DeleteControls } from '../../components/ui/DeleteControls'
import { toErrorMessage } from '../../lib/errorMessage'
import { useDeleteDocument, type DocumentKind } from '../../lib/queries'

type Tone = 'navy' | 'brand' | 'amber'

const TONE_STYLES: Record<Tone, string> = {
  navy: 'bg-navy/10 text-navy',
  brand: 'bg-brand/10 text-brand',
  amber: 'bg-amber-50 text-amber-600',
}

export interface PreviewStat {
  icon: React.ReactNode
  value: React.ReactNode
  label: string
  tone?: Tone
}

interface DocumentPreviewCardProps {
  icon: React.ReactNode
  title: string
  subtitle?: string
  id: number
  kind: DocumentKind
  stats?: PreviewStat[]
  // Called after the document is deleted; "Change" only clears the choice.
  onDeleted: () => void
  onChange: () => void
  children: React.ReactNode
}

// Preview of the chosen resume/JD, with delete (permanent) and Change
export function DocumentPreviewCard({
  icon,
  title,
  subtitle,
  id,
  kind,
  stats,
  onDeleted,
  onChange,
  children,
}: DocumentPreviewCardProps) {
  const remove = useDeleteDocument(kind)
  const dim = remove.isPending ? 'opacity-50' : ''

  return (
    <div
      aria-busy={remove.isPending}
      className="rounded-2xl bg-white border border-mist overflow-hidden shadow-[0_1px_2px_rgba(10,23,48,0.04)]"
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3 px-5 sm:px-6 py-5 bg-[#f8fafc] border-b border-mist">
        <div className={`flex items-center gap-4 flex-1 min-w-0 basis-48 transition-opacity ${dim}`}>
          <div className="w-12 h-12 rounded-2xl bg-navy text-white flex items-center justify-center shrink-0">
            {icon}
          </div>
          <div className="min-w-0">
            <p className="text-[17px] font-semibold text-ink leading-snug">{title}</p>
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
        </div>
        <DeleteControls
          label={kind}
          isDeleting={remove.isPending}
          errorMessage={remove.error ? toErrorMessage(remove.error, `Could not delete this ${kind}.`) : null}
          onConfirm={() => remove.mutate(id, { onSuccess: onDeleted })}
        >
          <button
            type="button"
            onClick={onChange}
            className="px-3 py-1.5 rounded-lg bg-white border border-mist text-xs font-semibold text-navy hover:border-navy/40 cursor-pointer"
          >
            Change
          </button>
        </DeleteControls>
      </div>

      {stats && stats.length > 0 && (
        <dl className={`grid grid-cols-3 divide-x divide-mist border-b border-mist transition-opacity ${dim}`}>
          {stats.map((stat) => (
            <div key={stat.label} className="flex items-center gap-3 px-4 sm:px-6 py-4">
              <div
                className={`hidden sm:flex w-9 h-9 rounded-xl items-center justify-center shrink-0 ${TONE_STYLES[stat.tone ?? 'navy']}`}
              >
                {stat.icon}
              </div>
              <div className="min-w-0">
                <dd className="text-[17px] font-bold text-ink leading-none truncate">{stat.value}</dd>
                <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted mt-1.5">
                  {stat.label}
                </dt>
              </div>
            </div>
          ))}
        </dl>
      )}

      <div className={`px-5 sm:px-6 py-5 space-y-6 transition-opacity ${dim}`}>{children}</div>
    </div>
  )
}

export function PreviewSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
}) {
  return (
    <section>
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted mb-3">
        <span className="w-4 h-4 inline-flex">{icon}</span>
        {title}
      </h3>
      {children}
    </section>
  )
}

export interface TimelineItem {
  title: string
  meta?: string | null
  dates?: string | null
  description?: string | null
}

// Vertical timeline: one dot per entry on a shared rail.
export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="ml-1.5 border-l-2 border-mist space-y-5">
      {items.map((item, i) => (
        <li key={i} className="relative pl-5">
          <span className="absolute -left-1.75 top-1.5 w-3 h-3 rounded-full bg-white border-2 border-brand" aria-hidden="true" />
          <div className="flex flex-wrap items-baseline justify-between gap-x-3">
            <p className="text-[14px] font-semibold text-ink">{item.title}</p>
            {item.dates && <p className="text-xs text-muted">{item.dates}</p>}
          </div>
          {item.meta && <p className="text-[13px] text-muted mt-0.5">{item.meta}</p>}
          {item.description && (
            <p className="text-[13px] text-ink/80 mt-1.5 leading-relaxed line-clamp-3">{item.description}</p>
          )}
        </li>
      ))}
    </ol>
  )
}

const CHIP_TONES = {
  neutral: 'bg-[#f4f7fa] border-mist text-ink',
  brand: 'bg-brand/10 border-brand/30 text-[#0d6b5f]',
  navy: 'bg-navy/10 border-navy/20 text-navy',
} as const

export function Chips({
  items,
  max = 16,
  tone = 'neutral',
}: {
  items: string[]
  max?: number
  tone?: keyof typeof CHIP_TONES
}) {
  const shown = items.slice(0, max)
  const rest = items.length - shown.length
  return (
    <ul className="flex flex-wrap gap-1.5">
      {shown.map((item) => (
        <li key={item} className={`px-2.5 py-1 rounded-full border text-xs font-medium ${CHIP_TONES[tone]}`}>
          {item}
        </li>
      ))}
      {rest > 0 && <li className="px-2 py-1 text-xs text-muted">+{rest} more</li>}
    </ul>
  )
}
