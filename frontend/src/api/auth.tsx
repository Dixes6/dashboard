import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiError, setOnUnauthorized } from './client'
import { AuthContext } from './authContext'
import type { User, LoginCredentials } from './authContext'

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient()
  const [loginError, setLoginError] = useState<string | null>(null)

  useEffect(() => {
    setOnUnauthorized(() => {
      queryClient.setQueryData(['auth', 'me'], null)
      queryClient.clear()
    })
    return () => {
      setOnUnauthorized(null)
    }
  }, [queryClient])

  const {
    data: user = null,
    isLoading,
  } = useQuery<User | null>({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      try {
        return await apiClient<User>('/api/auth/me')
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          return null
        }
        throw err
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      setLoginError(null)
      return apiClient<User>('/api/auth/login', {
        method: 'POST',
        body: credentials,
      })
    },
    onSuccess: (newUser) => {
      setLoginError(null)
      queryClient.setQueryData(['auth', 'me'], newUser)
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setLoginError(err.detail)
      } else {
        setLoginError('Не удалось войти в систему')
      }
    },
  })

  const logoutMutation = useMutation({
    mutationFn: async () => {
      return apiClient<{ status: string }>('/api/auth/logout', {
        method: 'POST',
      })
    },
    onSettled: () => {
      queryClient.setQueryData(['auth', 'me'], null)
      queryClient.clear()
      window.location.href = '/login'
    },
  })

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      return await loginMutation.mutateAsync(credentials)
    },
    [loginMutation],
  )

  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync()
  }, [logoutMutation])

  const clearLoginError = useCallback(() => {
    setLoginError(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isLoggingIn: loginMutation.isPending,
      loginError,
      login,
      logout,
      clearLoginError,
    }),
    [user, isLoading, loginMutation.isPending, loginError, login, logout, clearLoginError],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
