import { type ReactNode, useCallback, useEffect, useState } from 'react'

import type { Route } from '../../app/navigation'
import { useAuth } from '../../features/auth/AuthContext'
import { initials } from '../../lib/format'
import { api } from '../../lib/api'
import type { Notification, Page } from '../../lib/types'

const navigationItems: Array<{ route: Route; label: string; icon: string; adminOnly?: boolean; operationalOnly?: boolean }> = [
  { route: 'dashboard', label: 'Visão geral', icon: '▦' },
  { route: 'assets', label: 'Ativos', icon: '□' },
  { route: 'operations', label: 'Operações', icon: '↔' },
  { route: 'notifications', label: 'Notificações', icon: '●' },
  { route: 'reports', label: 'Relatórios', icon: '↓', operationalOnly: true },
  { route: 'catalogs', label: 'Cadastros', icon: '≡', adminOnly: true },
]

interface AppShellProps {
  route: Route
  onNavigate: (route: Route) => void
  children: ReactNode
}

export function AppShell({ route, onNavigate, children }: AppShellProps) {
  const { user, logout } = useAuth()
  const [unread, setUnread] = useState(0)

  const loadUnread = useCallback(async () => {
    try {
      const page = await api<Page<Notification>>('/api/v1/inventory/notifications/?read_at__isnull=true')
      setUnread(page.count)
    } catch {
      setUnread(0)
    }
  }, [])

  useEffect(() => {
    if (!user) return
    void loadUnread()
    window.addEventListener('notifications:changed', loadUnread)
    return () => window.removeEventListener('notifications:changed', loadUnread)
  }, [loadUnread, user])

  if (!user) return null

  const displayName = user.full_name || user.username

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand brand-button" onClick={() => onNavigate('dashboard')}>
          <span className="brand-mark">IT</span>
          <span>Inventário de TI</span>
        </button>
        <nav aria-label="Navegação principal">
          {navigationItems.filter((item) => (!item.adminOnly || user.role === 'ADMIN') && (!item.operationalOnly || user.role !== 'USER')).map((item) => (
            <button
              key={item.route}
              className={`nav-item ${route === item.route ? 'active' : ''}`}
              onClick={() => onNavigate(item.route)}
            >
              <span aria-hidden="true">{item.icon}</span>{item.label}
              {item.route === 'notifications' && unread > 0 && <strong className="nav-badge">{unread > 99 ? '99+' : unread}</strong>}
            </button>
          ))}
        </nav>
        <div className="sidebar-help">
          <strong>Controle com rastreabilidade</strong>
          <small>Todas as operações relevantes ficam registradas na auditoria.</small>
        </div>
        <div className="user-menu">
          <span className="user-avatar">{initials(displayName)}</span>
          <div><strong>{displayName}</strong><small>{user.role_display}</small></div>
          <button type="button" onClick={logout}>Sair</button>
        </div>
      </aside>
      <main className="page-content">{children}</main>
    </div>
  )
}
