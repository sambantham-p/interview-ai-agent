interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}


export function ErrorState({
  message = 'Something went wrong loading this.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6 rounded-2xl border border-red-200 bg-red-50">
      <p className="text-[15px] font-semibold text-red-700">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 text-sm font-semibold text-red-700 underline underline-offset-2 hover:text-red-800 cursor-pointer"
        >
          Try again
        </button>
      )}
    </div>
  )
}
