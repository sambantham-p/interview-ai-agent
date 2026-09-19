import { Card } from '../../components/ui/Card'
import { DeleteControls } from '../../components/ui/DeleteControls'
import { toErrorMessage } from '../../lib/errorMessage'
import { useDeleteDocument, type DocumentKind } from '../../lib/queries'

interface DocumentCardProps {
  id: number
  kind: DocumentKind
  chip: React.ReactNode
  children: React.ReactNode
}

// A document list card with a delete action.
export function DocumentCard({ id, kind, chip, children }: DocumentCardProps) {
  const remove = useDeleteDocument(kind)

  return (
    <Card interactive className="overflow-hidden" aria-busy={remove.isPending}>
      <div className="flex flex-wrap items-start gap-x-3.5 gap-y-3">
        <div className={`flex items-start gap-3.5 flex-1 min-w-0 basis-48 transition-opacity ${remove.isPending ? 'opacity-50' : ''}`}>
          {chip}
          <div className="min-w-0 flex-1">{children}</div>
        </div>
        <DeleteControls
          label={kind}
          isDeleting={remove.isPending}
          errorMessage={remove.error ? toErrorMessage(remove.error, `Could not delete this ${kind}.`) : null}
          onConfirm={() => remove.mutate(id)}
        />
      </div>
    </Card>
  )
}
