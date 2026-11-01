import type { ReactNode } from 'react'

import type { Route } from '../../app/navigation'
import { useAuth } from '../../features/auth/AuthContext'
import { initials } from '../../lib/format'

const navigationItems: Array<{ route: Route; label: string; icon: string; adminOnly?: boolean }> = [
  { route: 'dashboard', label: 'Visão geral', icon: '▦' },
  { route: 'assets', label: 'Ativos', icon: '□' },
  { route: 'operations', label: 'Operações', icon: '↔' },
  { route: 'catalogs', label: 'Cadastros', icon: '≡', adminOnly: true },
]

interface AppShellProps {
  route: Route
  onNavigate: (route: Route) => void
  children: ReactNode
}

export function AppShell({ route, onNavigate, children }: AppShellProps) {
  const { user, logout } = useAuth()
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
          {navigationItems.filter((item) => !item.adminOnly || user.role === 'ADMIN').map((item) => (
            <button
              key={item.route}
              className={`nav-item ${route === item.route ? 'active' : ''}`}
              onClick={() => onNavigate(item.route)}
            >
              <span aria-hidden="true">{item.icon}</span>{item.label}
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
