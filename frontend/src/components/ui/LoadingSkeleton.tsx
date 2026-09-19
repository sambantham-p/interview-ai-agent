import { Card } from './Card'

interface LoadingSkeletonProps {
  rows?: number
  variant?: 'row' | 'grid'
}

function Bar({ className = '' }: { className?: string }) {
  return (
    <div
      className={`shimmer relative overflow-hidden rounded-md bg-[#e9eef4] ${className}`}
    />
  )
}

function SkeletonCard() {
  return (
    <Card className="flex items-center gap-3.5">
      <Bar className="w-10 h-10 rounded-xl shrink-0" />
      <div className="flex-1 min-w-0 space-y-2">
        <Bar className="h-3.5 w-2/5" />
        <Bar className="h-3 w-3/5" />
      </div>
    </Card>
  )
}

function SkeletonRow() {
  return (
    <Card className="flex items-center justify-between gap-4 py-4">
      <div className="flex items-center gap-3.5 min-w-0 flex-1">
        <Bar className="w-9 h-9 rounded-lg shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <Bar className="h-3.5 w-1/3" />
          <Bar className="h-3 w-1/4" />
        </div>
      </div>
      <Bar className="h-6 w-20 rounded-full shrink-0" />
    </Card>
  )
}

export function LoadingSkeleton({ rows = 3, variant = 'row' }: LoadingSkeletonProps) {
  if (variant === 'grid') {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="status" aria-label="Loading">
        {Array.from({ length: rows }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  )
}
