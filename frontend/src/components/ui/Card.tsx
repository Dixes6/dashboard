import React from 'react'
import type { HTMLAttributes } from 'react'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export const Card: React.FC<CardProps> = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`bg-surface border border-border rounded-card p-5 shadow-soft text-text ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
