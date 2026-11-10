import React, { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../api'
import { Button, Input, Spinner } from '../components/ui'

export const LoginPage: React.FC = () => {
  const { user, isLoading, isLoggingIn, loginError, login, clearLoginError } = useAuth()
  const [loginValue, setLoginValue] = useState('')
  const [passwordValue, setPasswordValue] = useState('')

  if (isLoading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-bg">
        <Spinner size="lg" />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!loginValue.trim() || !passwordValue.trim()) return
    try {
      await login({
        login: loginValue.trim(),
        password: passwordValue,
      })
    } catch {
      // Handled in AuthProvider state (loginError)
    }
  }

  return (
    <div className="min-h-[100dvh] flex flex-col items-center justify-center px-4 py-8 bg-gradient-to-b from-bg to-primary-soft text-text font-sans">
      <div className="w-full max-w-sm bg-surface border border-border rounded-card p-6 sm:p-8 shadow-soft flex flex-col gap-6">
        <div className="text-center">
          <h1 className="text-4xl font-heading font-semibold text-text tracking-wide">
            Dashboard
          </h1>
          <p className="text-sm text-muted mt-1.5">
            Вход в систему мастера
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Логин"
            type="text"
            placeholder="Введите логин"
            value={loginValue}
            onChange={(e) => {
              setLoginValue(e.target.value)
              if (loginError) clearLoginError()
            }}
            autoComplete="username"
            autoCapitalize="none"
            required
          />

          <Input
            label="Пароль"
            type="password"
            placeholder="Введите пароль"
            value={passwordValue}
            onChange={(e) => {
              setPasswordValue(e.target.value)
              if (loginError) clearLoginError()
            }}
            autoComplete="current-password"
            required
          />

          {loginError ? (
            <div
              role="alert"
              className="text-xs text-danger font-medium p-2.5 rounded-btn bg-danger/10 border border-danger/20 text-center"
            >
              {loginError}
            </div>
          ) : null}

          <Button
            type="submit"
            variant="primary"
            loading={isLoggingIn}
            disabled={!loginValue.trim() || !passwordValue.trim()}
            className="w-full mt-2"
          >
            Войти
          </Button>
        </form>
      </div>
    </div>
  )
}
