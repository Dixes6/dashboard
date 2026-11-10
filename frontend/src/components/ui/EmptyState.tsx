import React from 'react'

export interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center p-8 text-muted ${className}`}
    >
      {icon ? <div className="mb-4 text-accent">{icon}</div> : null}
      <h3 className="text-xl font-heading font-semibold text-text mb-1">{title}</h3>
      {description ? (
        <p className="text-sm text-muted max-w-xs mb-4">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}
