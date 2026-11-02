import { useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { formatCurrency, formatDate } from '../../lib/format'
import type { Asset, Loan, Maintenance, Page, ResponsiblePerson, Sector } from '../../lib/types'
import { useAuth } from '../auth/AuthContext'
import { FinishOperationForm, type FinishTarget, LoanForm, MaintenanceForm } from './OperationForms'
import { ResponsiblePeoplePanel } from './ResponsiblePeoplePanel'

type NewOperation = 'loan' | 'maintenance' | null

export function OperationsPage() {
  const { user } = useAuth()
  const canOperate = user?.role === 'TECHNICIAN' || user?.role === 'ADMIN'
  const canDelete = user?.role === 'ADMIN'
  const [loans, setLoans] = useState<Loan[] | null>(null)
  const [maintenances, setMaintenances] = useState<Maintenance[] | null>(null)
  const [assets, setAssets] = useState<Asset[]>([])
  const [people, setPeople] = useState<ResponsiblePerson[]>([])
  const [sectors, setSectors] = useState<Sector[]>([])
  const [newOperation, setNewOperation] = useState<NewOperation>(null)
  const [finishTarget, setFinishTarget] = useState<FinishTarget | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [loanPage, maintenancePage, assetPage, peoplePage, sectorPage] = await Promise.all([
        api<Page<Loan>>('/api/v1/inventory/loans/?ordering=-created_at'),
        api<Page<Maintenance>>('/api/v1/inventory/maintenances/?ordering=-created_at'),
        api<Page<Asset>>('/api/v1/inventory/assets/?ordering=asset_tag'),
        api<Page<ResponsiblePerson>>('/api/v1/inventory/responsible-people/?ordering=name'),
        api<Page<Sector>>('/api/v1/inventory/sectors/?ordering=name'),
      ])
      setLoans(loanPage.results)
      setMaintenances(maintenancePage.results)
      setAssets(assetPage.results)
      setPeople(peoplePage.results)
      setSectors(sectorPage.results)
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar as operações.')
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const saved = async () => {
    setNewOperation(null)
    setFinishTarget(null)
    await load()
  }

  return (
    <>
      <PageHeader
        eyebrow="OPERAÇÕES"
        title="Empréstimos e manutenções"
        description="Registre a circulação e a indisponibilidade dos equipamentos."
        action={canOperate ? <div className="header-actions"><button className="secondary-button" onClick={() => setNewOperation('maintenance')}>+ Manutenção</button><button className="primary-button" onClick={() => setNewOperation('loan')}>+ Empréstimo</button></div> : <button className="secondary-button" onClick={load}>Atualizar</button>}
      />
      {loans === null && maintenances === null && !error && <LoadingState label="Carregando operações..." />}
      {error && <ErrorState message={error} retry={load} />}
      {loans && maintenances && (
        <>
          <section className="operations-grid">
            <article className="panel">
              <div className="panel-heading"><div><p className="eyebrow">MOVIMENTAÇÃO</p><h2>Empréstimos recentes</h2></div><span className="count-badge">{loans.length}</span></div>
              {!loans.length ? <EmptyState title="Sem empréstimos" description="Os novos empréstimos aparecerão aqui." /> : <div className="compact-list">{loans.map((loan) => (
                <article key={loan.id}><div><strong>{loan.asset_tag}</strong><span>{loan.borrower_name}</span><small>De {formatDate(loan.loaned_at)} até {formatDate(loan.expected_return_date)}</small></div><div className="align-right"><span className={`status-pill ${loan.is_active ? 'warning' : 'success'}`}>{loan.is_active ? 'Em aberto' : 'Devolvido'}</span>{canOperate && loan.is_active && <button className="text-button" onClick={() => setFinishTarget({ kind: 'return', loan })}>Registrar devolução</button>}</div></article>
              ))}</div>}
            </article>
            <article className="panel">
              <div className="panel-heading"><div><p className="eyebrow">SUPORTE</p><h2>Manutenções recentes</h2></div><span className="count-badge">{maintenances.length}</span></div>
              {!maintenances.length ? <EmptyState title="Sem manutenções" description="As ordens de manutenção aparecerão aqui." /> : <div className="compact-list">{maintenances.map((maintenance) => (
                <article key={maintenance.id}><div><strong>{maintenance.asset_tag}</strong><span>{maintenance.maintenance_type_display} · {maintenance.provider || 'Sem prestador'}</span><small>{maintenance.description}</small></div><div className="align-right"><span className={`status-pill ${maintenance.is_active ? 'warning' : 'success'}`}>{maintenance.status_display}</span><small>{maintenance.cost ? formatCurrency(maintenance.cost) : formatDate(maintenance.started_at)}</small>{canOperate && maintenance.is_active && <div className="row-actions"><button className="text-button" onClick={() => setFinishTarget({ kind: 'complete', maintenance })}>Concluir</button><button className="text-button danger" onClick={() => setFinishTarget({ kind: 'cancel', maintenance })}>Cancelar</button></div>}</div></article>
              ))}</div>}
            </article>
          </section>
          <ResponsiblePeoplePanel people={people} sectors={sectors} canEdit={Boolean(canOperate)} canDelete={Boolean(canDelete)} onChanged={load} />
        </>
      )}
      {newOperation === 'loan' && <LoanForm assets={assets} people={people} onClose={() => setNewOperation(null)} onSaved={saved} />}
      {newOperation === 'maintenance' && <MaintenanceForm assets={assets} onClose={() => setNewOperation(null)} onSaved={saved} />}
      {finishTarget && <FinishOperationForm target={finishTarget} onClose={() => setFinishTarget(null)} onSaved={saved} />}
    </>
  )
}
