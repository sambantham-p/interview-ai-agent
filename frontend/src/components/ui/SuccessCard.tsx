import { Button } from './Button'

interface SuccessCardProps {
  title: string
  message: string
  ctaLabel: string
  onCta: () => void
}


export function SuccessCard({ title, message, ctaLabel, onCta }: SuccessCardProps) {
  return (
    <div className="w-full flex flex-col gap-6">
      <div className="bg-[#ddf6f1] flex flex-col gap-2 p-4.5 rounded-[10px]">
        <p aria-hidden="true" className="text-brand text-[24px] leading-none">
          ✓
        </p>
        <p className="text-ink text-[14px] font-bold">{title}</p>
        <p className="text-muted text-[12px] leading-relaxed">{message}</p>
      </div>
      <Button type="button" variant="primary" onClick={onCta}>
        {ctaLabel}
      </Button>
    </div>
  )
}
