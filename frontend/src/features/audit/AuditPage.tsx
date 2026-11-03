import { Fragment, useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { formatDateTime } from '../../lib/format'
import type { AuditLog, Page } from '../../lib/types'

export function AuditPage() {
  const [logs, setLogs] = useState<Page<AuditLog> | null>(null)
  const [search, setSearch] = useState('')
  const [action, setAction] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [page, setPage] = useState(1)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    const params = new URLSearchParams({ page: String(page), ordering: '-created_at' })
    if (search) params.set('search', search)
    if (action) params.set('action', action)
    if (startDate) params.set('created_at__gte', `${startDate}T00:00:00`)
    if (endDate) params.set('created_at__lte', `${endDate}T23:59:59`)
    try {
      setLogs(await api<Page<AuditLog>>(`/api/v1/inventory/audit-logs/?${params}`))
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar a auditoria.')
    }
  }, [action, endDate, page, search, startDate])

  useEffect(() => { void load() }, [load])

  const clearFilters = () => {
    setSearch('')
    setAction('')
    setStartDate('')
    setEndDate('')
    setPage(1)
  }

  return (
    <>
      <PageHeader eyebrow="GOVERNANÇA" title="Trilha de auditoria" description="Consulte alterações, exclusões e ações operacionais registradas pelo sistema." action={<button className="secondary-button" onClick={load}>Atualizar</button>} />
      <section className="filter-bar audit-filter">
        <label>Buscar<input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Usuário, recurso ou rota" /></label>
        <label>Ação<select value={action} onChange={(event) => { setAction(event.target.value); setPage(1) }}><option value="">Todas</option><option value="CREATE">Criação</option><option value="UPDATE">Alteração</option><option value="DELETE">Exclusão</option><option value="ACTION">Ação operacional</option><option value="SCAN">Leitura de QR Code</option></select></label>
        <label>Data inicial<input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPage(1) }} /></label>
        <label>Data final<input type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setPage(1) }} /></label>
        <button className="secondary-button" onClick={clearFilters}>Limpar</button>
      </section>
      {!logs && !error ? <LoadingState label="Carregando auditoria..." /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {logs && !logs.results.length ? <EmptyState title="Nenhum registro encontrado" description="Ajuste os filtros para consultar outras ações." /> : null}
      {logs && logs.results.length ? <><div className="table-card"><table><thead><tr><th>Ação</th><th>Recurso</th><th>Usuário</th><th>Data</th><th aria-label="Detalhes" /></tr></thead><tbody>{logs.results.map((log) => <Fragment key={log.id}><tr className="audit-row"><td><span className={`audit-action ${log.action.toLowerCase()}`}>{log.action_display}</span></td><td><strong>{log.object_repr}</strong><span>{log.resource_type} · #{log.object_id}</span></td><td>{log.actor_username || 'Sistema'}</td><td>{formatDateTime(log.created_at)}</td><td><button className="text-button" onClick={() => setExpandedId((current) => current === log.id ? null : log.id)} aria-expanded={expandedId === log.id}>{expandedId === log.id ? 'Ocultar' : 'Detalhes'}</button></td></tr>{expandedId === log.id ? <tr className="audit-detail-row"><td colSpan={5}><div className="audit-details"><dl><div><dt>Requisição</dt><dd>{log.method || '—'} {log.path || '—'}</dd></div><div><dt>IP</dt><dd>{log.ip_address || 'Não informado'}</dd></div><div><dt>ID da requisição</dt><dd>{log.request_id}</dd></div></dl><pre>{JSON.stringify(log.changes, null, 2)}</pre></div></td></tr> : null}</Fragment>)}</tbody></table></div><div className="pagination"><button className="secondary-button" disabled={!logs.previous} onClick={() => setPage((value) => value - 1)}>Anterior</button><span>Página {page} · {logs.count} registro(s)</span><button className="secondary-button" disabled={!logs.next} onClick={() => setPage((value) => value + 1)}>Próxima</button></div></> : null}
    </>
  )
}
