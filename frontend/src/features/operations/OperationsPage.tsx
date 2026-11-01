import { useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { formatCurrency, formatDate } from '../../lib/format'
import type { Page } from '../../lib/types'

interface Loan {
  id: number
  asset_tag: string
  borrower_name: string
  loaned_at: string
  expected_return_date: string
  returned_at: string | null
  is_active: boolean
}

interface Maintenance {
  id: number
  asset_tag: string
  maintenance_type_display: string
  status_display: string
  description: string
  provider: string
  started_at: string
  completed_at: string | null
  cost: string | null
  is_active: boolean
}

export function OperationsPage() {
  const [loans, setLoans] = useState<Loan[] | null>(null)
  const [maintenances, setMaintenances] = useState<Maintenance[] | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [loanPage, maintenancePage] = await Promise.all([
        api<Page<Loan>>('/api/v1/inventory/loans/?ordering=-created_at'),
        api<Page<Maintenance>>('/api/v1/inventory/maintenances/?ordering=-created_at'),
      ])
      setLoans(loanPage.results)
      setMaintenances(maintenancePage.results)
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar as operações.')
    }
  }, [])

  useEffect(() => { void load() }, [load])

  return (
    <>
      <PageHeader eyebrow="OPERAÇÕES" title="Empréstimos e manutenções" description="Acompanhe a circulação e a indisponibilidade dos equipamentos." action={<button className="secondary-button" onClick={load}>Atualizar</button>} />
      {loans === null && maintenances === null && !error && <LoadingState label="Carregando operações..." />}
      {error && <ErrorState message={error} retry={load} />}
      {loans && maintenances && (
        <section className="operations-grid">
          <article className="panel">
            <div className="panel-heading"><div><p className="eyebrow">MOVIMENTAÇÃO</p><h2>Empréstimos recentes</h2></div><span className="count-badge">{loans.length}</span></div>
            {!loans.length ? <EmptyState title="Sem empréstimos" description="Os novos empréstimos aparecerão aqui." /> : <div className="compact-list">{loans.map((loan) => (
              <article key={loan.id}><div><strong>{loan.asset_tag}</strong><span>{loan.borrower_name}</span></div><div className="align-right"><span className={`status-pill ${loan.is_active ? 'warning' : 'success'}`}>{loan.is_active ? 'Em aberto' : 'Devolvido'}</span><small>Previsto: {formatDate(loan.expected_return_date)}</small></div></article>
            ))}</div>}
          </article>
          <article className="panel">
            <div className="panel-heading"><div><p className="eyebrow">SUPORTE</p><h2>Manutenções recentes</h2></div><span className="count-badge">{maintenances.length}</span></div>
            {!maintenances.length ? <EmptyState title="Sem manutenções" description="As ordens de manutenção aparecerão aqui." /> : <div className="compact-list">{maintenances.map((maintenance) => (
              <article key={maintenance.id}><div><strong>{maintenance.asset_tag}</strong><span>{maintenance.maintenance_type_display} · {maintenance.provider || 'Sem prestador'}</span><small>{maintenance.description}</small></div><div className="align-right"><span className={`status-pill ${maintenance.is_active ? 'warning' : 'success'}`}>{maintenance.status_display}</span><small>{maintenance.cost ? formatCurrency(maintenance.cost) : formatDate(maintenance.started_at)}</small></div></article>
            ))}</div>}
          </article>
        </section>
      )}
    </>
  )
}
