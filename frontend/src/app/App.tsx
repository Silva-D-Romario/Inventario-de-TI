import { useEffect, useState } from 'react'

import { AppShell } from '../components/layout/AppShell'
import { AssetsPage } from '../features/assets/AssetsPage'
import { AuthPage } from '../features/auth/AuthPage'
import { useAuth } from '../features/auth/AuthContext'
import { CatalogsPage } from '../features/catalogs/CatalogsPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { NotificationsPage } from '../features/notifications/NotificationsPage'
import { OperationsPage } from '../features/operations/OperationsPage'
import { ReportsPage } from '../features/reports/ReportsPage'
import { navigation, type Route } from './navigation'

export function App() {
  const { user, loading } = useAuth()
  const [route, setRoute] = useState<Route>(navigation.current)

  useEffect(() => {
    const syncRoute = () => setRoute(navigation.current())
    window.addEventListener('hashchange', syncRoute)
    return () => window.removeEventListener('hashchange', syncRoute)
  }, [])

  if (loading) return <div className="loading-screen"><span className="loader" /> Validando sessão...</div>
  if (!user) return <AuthPage />

  return (
    <AppShell route={route} onNavigate={navigation.go}>
      {route === 'dashboard' && <DashboardPage />}
      {route === 'assets' && <AssetsPage />}
      {route === 'operations' && <OperationsPage />}
      {route === 'notifications' && <NotificationsPage />}
      {route === 'reports' && <ReportsPage />}
      {route === 'catalogs' && <CatalogsPage />}
    </AppShell>
  )
}
