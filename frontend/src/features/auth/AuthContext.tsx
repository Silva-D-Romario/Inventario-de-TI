import { createContext, use, useCallback, useEffect, useMemo, useState } from 'react'

import { api, tokenStorage } from '../../lib/api'
import type { User } from '../../lib/types'

interface LoginCredentials {
  username: string
  password: string
}

interface RegistrationData extends LoginCredentials {
  email: string
  first_name: string
  last_name: string
  password_confirmation: string
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegistrationData) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(tokenStorage.hasSession())

  const loadUser = useCallback(async () => {
    const currentUser = await api<User>('/api/v1/auth/me/')
    setUser(currentUser)
  }, [])

  useEffect(() => {
    if (!tokenStorage.hasSession()) return
    loadUser()
      .catch(() => tokenStorage.clear())
      .finally(() => setLoading(false))
  }, [loadUser])

  const login = async (credentials: LoginCredentials) => {
    const tokens = await api<{ access: string; refresh: string }>('/api/v1/auth/token/', {
      method: 'POST',
      body: JSON.stringify(credentials),
      retry: false,
    })
    tokenStorage.save(tokens.access, tokens.refresh)
    await loadUser()
  }

  const register = async (data: RegistrationData) => {
    await api('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
      retry: false,
    })
    await login({ username: data.username, password: data.password })
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
  }

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth() {
  const context = use(AuthContext)
  if (!context) throw new Error('useAuth precisa estar dentro de AuthProvider.')
  return context
}
