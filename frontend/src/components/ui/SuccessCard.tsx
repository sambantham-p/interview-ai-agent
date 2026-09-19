import { Button } from './Button'
import { CheckCircleIcon } from './icons'

interface SuccessCardProps {
  title: string
  message: string
  ctaLabel: string
  onCta: () => void
}


export function SuccessCard({ title, message, ctaLabel, onCta }: SuccessCardProps) {
  return (
    <div className="w-full flex flex-col gap-6">
      <div className="bg-[#ddf6f1] flex items-start gap-3 p-4 rounded-[10px]">
        <CheckCircleIcon className="mt-0.5 h-5 w-5 shrink-0 text-brand" />
        <div className="flex flex-col gap-0.5">
          <p className="text-ink text-[14px] font-bold">{title}</p>
          <p className="text-muted text-[12px] leading-relaxed">{message}</p>
        </div>
      </div>
      <Button type="button" variant="primary" onClick={onCta}>
        {ctaLabel}
      </Button>
    </div>
  )
}
