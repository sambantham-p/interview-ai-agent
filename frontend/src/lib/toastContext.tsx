import { createContext, useContext } from 'react'

export type ToastVariant = 'success' | 'error'

export interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

export interface ToastContextType {
  showToast: (message: string, variant?: ToastVariant) => void
}

export const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within a ToastProvider')
  return context
}
