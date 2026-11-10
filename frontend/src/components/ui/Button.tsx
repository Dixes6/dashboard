import React from 'react'
import type { ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  loading?: boolean
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  loading = false,
  disabled,
  children,
  className = '',
  ...props
}) => {
  const baseClasses =
    'h-12 min-h-[48px] px-5 rounded-btn font-medium text-base inline-flex items-center justify-center gap-2 transition-colors duration-150 select-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none'

  const variantClasses = {
    primary:
      'bg-primary text-surface hover:opacity-90 active:opacity-80 shadow-soft',
    secondary:
      'bg-primary-soft text-primary hover:bg-border/60 active:bg-border/80 border border-border',
    danger:
      'bg-danger text-surface hover:opacity-90 active:opacity-80 shadow-soft',
  }

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Spinner size="sm" className="border-t-current border-current/30" /> : null}
      <span>{children}</span>
    </button>
  )
}
