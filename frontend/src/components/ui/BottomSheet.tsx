import React, { useEffect } from 'react'

export interface BottomSheetProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className = '',
}) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-text/40 transition-opacity duration-150 cursor-pointer"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Модальное окно'}
        className={`relative z-10 w-full max-w-[480px] mx-auto bg-surface border-t border-border rounded-t-card p-6 shadow-2xl flex flex-col max-h-[85vh] transition-transform duration-150 pb-[calc(1.5rem+env(safe-area-inset-bottom))] ${className}`}
      >
        <div className="w-10 h-1 bg-border rounded-full mx-auto mb-4" />
        {title ? (
          <div className="flex items-center justify-between pb-3 border-b border-border mb-4">
            <h2 className="text-xl font-heading font-semibold text-text">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="text-muted hover:text-text p-1 min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer rounded-btn focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label="Закрыть"
            >
              ✕
            </button>
          </div>
        ) : null}
        <div className="overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}
