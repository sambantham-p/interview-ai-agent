interface PageIntroProps {
  title?: string
  description: React.ReactNode
  action?: React.ReactNode
}

export function PageIntro({ title, description, action }: PageIntroProps) {
  return (
    <div className="flex items-start justify-between gap-4 flex-wrap">
      <div className="max-w-2xl">
        {title && (
          <h2 className="font-display text-[28px] font-bold leading-tight tracking-tight text-ink">
            {title}
          </h2>
        )}
        <p
          className={`text-[15px] leading-relaxed text-slate-600 ${title ? 'mt-2' : ''}`}
        >
          {description}
        </p>
      </div>
      {action}
    </div>
  )
}
