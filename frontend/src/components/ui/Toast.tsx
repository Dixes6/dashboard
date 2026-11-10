import React, { useState, useCallback, useMemo } from 'react'
import { ToastContext } from './ToastContext'
import type { ToastMessage } from './ToastContext'

export interface ToastProviderProps {
  children: React.ReactNode
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const showToast = useCallback((text: string, type: 'info' | 'success' | 'danger' = 'info') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id, text, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3000)
  }, [])

  const contextValue = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-full max-w-xs px-4 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            className={`pointer-events-auto px-4 py-3 rounded-btn border text-sm font-medium shadow-soft text-center transition-all duration-150 animate-in fade-in slide-in-from-top-2 ${
              toast.type === 'danger'
                ? 'bg-surface text-danger border-danger'
                : toast.type === 'success'
                ? 'bg-surface text-success border-success'
                : 'bg-surface text-text border-border'
            }`}
          >
            {toast.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export interface ToastProps {
  message: string
  type?: 'info' | 'success' | 'danger'
  onClose?: () => void
  className?: string
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  onClose,
  className = '',
}) => {
  return (
    <div
      role="alert"
      className={`px-4 py-3 rounded-btn border text-sm font-medium shadow-soft flex items-center justify-between gap-3 ${
        type === 'danger'
          ? 'bg-surface text-danger border-danger'
          : type === 'success'
          ? 'bg-surface text-success border-success'
          : 'bg-surface text-text border-border'
      } ${className}`}
    >
      <span>{message}</span>
      {onClose ? (
        <button
          type="button"
          onClick={onClose}
          className="text-muted hover:text-text cursor-pointer p-1"
          aria-label="Закрыть"
        >
          ✕
        </button>
      ) : null}
    </div>
  )
}
