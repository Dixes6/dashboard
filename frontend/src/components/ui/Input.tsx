import { forwardRef, useId } from 'react'
import type { InputHTMLAttributes } from 'react'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, className = '', ...props }, ref) => {
    const generatedId = useId()
    const inputId = id || generatedId
    const errorId = `${inputId}-error`

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label ? (
          <label htmlFor={inputId} className="text-sm font-medium text-text">
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          className={`h-12 min-h-[48px] px-4 rounded-btn bg-surface border text-text placeholder:text-muted transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 focus-visible:ring-offset-surface disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-danger focus-visible:ring-danger' : 'border-border'
          } ${className}`}
          {...props}
        />
        {error ? (
          <span id={errorId} className="text-xs text-danger font-medium mt-0.5">
            {error}
          </span>
        ) : null}
      </div>
    )
  },
)

Input.displayName = 'Input'
