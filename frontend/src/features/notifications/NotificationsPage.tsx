import { useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { formatDateTime } from '../../lib/format'
import type { Notification, Page } from '../../lib/types'

const notifyChanged = () => window.dispatchEvent(new Event('notifications:changed'))

export function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[] | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const page = await api<Page<Notification>>('/api/v1/inventory/notifications/?ordering=-created_at')
      setNotifications(page.results)
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar as notificações.')
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const markRead = async (notification: Notification) => {
    try {
      await api(`/api/v1/inventory/notifications/${notification.id}/mark-read/`, { method: 'POST', body: '{}' })
      await load()
      notifyChanged()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível atualizar a notificação.')
    }
  }

  const markAllRead = async () => {
    try {
      await api('/api/v1/inventory/notifications/mark-all-read/', { method: 'POST', body: '{}' })
      await load()
      notifyChanged()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível atualizar as notificações.')
    }
  }

  const unread = notifications?.filter((notification) => !notification.is_read).length ?? 0

  return (
    <>
      <PageHeader eyebrow="ALERTAS" title="Notificações" description="Acompanhe empréstimos vencidos e garantias próximas do fim." action={unread > 0 && <button className="secondary-button" onClick={markAllRead}>Marcar todas como lidas</button>} />
      {!notifications && !error && <LoadingState label="Carregando notificações..." />}
      {error && <ErrorState message={error} retry={load} />}
      {notifications && !notifications.length && <EmptyState title="Tudo em dia" description="Você não possui notificações no momento." />}
      {notifications && notifications.length > 0 && <section className="notification-list">{notifications.map((notification) => (
        <article key={notification.id} className={notification.is_read ? 'read' : ''}>
          <span className={`notification-icon ${notification.alert_type.toLowerCase()}`}>!</span>
          <div><div className="notification-title"><strong>{notification.title}</strong><span>{notification.alert_type_display}</span></div><p>{notification.message}</p><small>{formatDateTime(notification.created_at)}</small></div>
          {!notification.is_read && <button className="text-button" onClick={() => markRead(notification)}>Marcar como lida</button>}
        </article>
      ))}</section>}
    </>
  )
}
