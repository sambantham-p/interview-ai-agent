interface MissingNoticeProps {
  // What the document is called in the sentence, e.g. "resume".
  subject: string
  items: string[]
  // Optional consequence, shown after the list.
  hint?: string
}


export function MissingNotice({ subject, items, hint }: MissingNoticeProps) {
  if (items.length === 0) return null

  return (
    <div
      role="note"
      className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-[13px] text-amber-800"
    >
      <span className="font-semibold">Not found in this {subject}:</span> {items.join(', ')}.
      {hint && <span> {hint}</span>}
    </div>
  )
}
