import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../api'
import { Spinner } from '../ui'
import { AppLayout } from './AppLayout'

export const ProtectedRoute: React.FC = () => {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-bg">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <AppLayout />
}
