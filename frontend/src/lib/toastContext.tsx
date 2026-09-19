import { createPortal } from 'react-dom'
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import { CheckCircleIcon, ExclamationCircleIcon } from '../components/ui/icons'

const TOAST_DURATION_MS = 3500

type ToastVariant = 'success' | 'error'

interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastContextType {
  showToast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(0)

  const showToast = useCallback(
    (message: string, variant: ToastVariant = 'success') => {
      const id = nextId.current++
      setToasts((current) => [...current, { id, message, variant }])
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id))
      }, TOAST_DURATION_MS)
    },
    [],
  )

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div
          aria-live="polite"
          className="pointer-events-none fixed bottom-6 right-6 z-100 flex flex-col gap-2"
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              role={toast.variant === 'error' ? 'alert' : 'status'}
              className="toast-in pointer-events-auto flex max-w-sm items-center gap-3 rounded-xl border border-mist bg-white px-4 py-3 text-sm font-medium text-ink shadow-[0_10px_30px_-12px_rgba(10,23,48,0.25)]"
            >
              {toast.variant === 'error' ? (
                <ExclamationCircleIcon className="h-5 w-5 shrink-0 text-red-500" />
              ) : (
                <CheckCircleIcon className="h-5 w-5 shrink-0 text-emerald-500" />
              )}
              {toast.message}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within a ToastProvider')
  return context
}
