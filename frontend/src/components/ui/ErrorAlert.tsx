interface ErrorAlertProps {
  message: string | null | undefined
}

// The one error-message box every auth form uses 
export function ErrorAlert({ message }: ErrorAlertProps) {
  if (!message) return null

  return (
    <div
      role="alert"
      className="p-3 bg-red-50 border border-red-200 text-red-700 text-[13px] rounded-[10px]"
    >
      {message}
    </div>
  )
}
