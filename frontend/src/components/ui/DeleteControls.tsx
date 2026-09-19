import { useState } from 'react'
import { ErrorAlert } from './ErrorAlert'
import { TrashIcon } from './icons'
import { Spinner } from './Spinner'

interface DeleteControlsProps {
  label: string
  isDeleting: boolean
  errorMessage: string | null
  onConfirm: () => void
  // Extra idle-state actions shown before the trash icon (e.g. "Change").
  children?: React.ReactNode
}


export function DeleteControls({
  label,
  isDeleting,
  errorMessage,
  onConfirm,
  children,
}: DeleteControlsProps) {
  const [confirming, setConfirming] = useState(false)

  return (
    <>
      {!isDeleting && !confirming && (
        <div className="flex items-center gap-1.5 shrink-0 ml-auto">
          {children}
          <button
            type="button"
            aria-label={`Delete ${label}`}
            onClick={() => setConfirming(true)}
            className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 focus-visible:text-red-600 focus-visible:bg-red-50 transition-colors cursor-pointer"
          >
            <TrashIcon className="w-4.5 h-4.5" />
          </button>
        </div>
      )}

      {isDeleting && (
        <div
          role="status"
          className="basis-full flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-[13px] font-medium text-red-800"
        >
          <Spinner />
          Deleting {label}…
        </div>
      )}

      {confirming && !isDeleting && (
        <div
          role="group"
          aria-label={`Confirm deleting ${label}`}
          className="basis-full flex items-center justify-between gap-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2"
        >
          <div className="text-[13px] text-red-800">
            <p className="font-medium">Delete this {label} permanently?</p>
            <p className="mt-0.5">
              Any completed interviews that used it, along with their reports, will be deleted
              too.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="px-3 py-1.5 rounded-lg bg-white border border-red-200 text-xs font-semibold text-red-800 hover:bg-red-100 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                setConfirming(false)
                onConfirm()
              }}
              className="px-3 py-1.5 rounded-lg bg-red-600 text-xs font-semibold text-white hover:bg-red-700 cursor-pointer"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="basis-full">
          <ErrorAlert message={errorMessage} />
        </div>
      )}
    </>
  )
}
