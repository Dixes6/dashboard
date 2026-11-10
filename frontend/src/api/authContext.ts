import { createContext } from 'react'
import type { components } from './schema'

export type User = components['schemas']['UserResponse']
export type LoginCredentials = components['schemas']['LoginRequest']

export interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isLoggingIn: boolean
  loginError: string | null
  login: (credentials: LoginCredentials) => Promise<User>
  logout: () => Promise<void>
  clearLoginError: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
