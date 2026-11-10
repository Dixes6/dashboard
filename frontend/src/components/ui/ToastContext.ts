import { createContext } from 'react'

export interface ToastMessage {
  id: string
  text: string
  type?: 'info' | 'success' | 'danger'
}

export interface ToastContextValue {
  showToast: (text: string, type?: 'info' | 'success' | 'danger') => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)
