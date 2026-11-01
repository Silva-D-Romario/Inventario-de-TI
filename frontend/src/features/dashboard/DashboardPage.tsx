import { useCallback, useEffect, useState } from 'react'

import { ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { formatCurrency, formatDateTime } from '../../lib/format'
import type { DashboardData, DistributionItem } from '../../lib/types'

function DistributionBars({ data }: { data: DistributionItem[] }) {
  const largest = Math.max(...data.map((item) => item.total), 1)
  return (
    <div className="distribution-list">
      {data.map((item) => (
        <div key={item.key} className="distribution-row">
          <div><span>{item.label}</span><strong>{item.total}</strong></div>
          <span className="progress-track"><span style={{ width: `${Math.max((item.total / largest) * 100, 4)}%` }} /></span>
        </div>
      ))}
    </div>
  )
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')

  const loadDashboard = useCallback(async () => {
    setError('')
    try {
      setData(await api<DashboardData>('/api/v1/inventory/dashboard/'))
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar os indicadores.')
    }
  }, [])

  useEffect(() => { void loadDashboard() }, [loadDashboard])

  return (
    <>
      <PageHeader eyebrow="PAINEL OPERACIONAL" title="Visão geral" description="Acompanhe o patrimônio e as operações mais importantes." action={<button className="secondary-button" onClick={loadDashboard}>Atualizar dados</button>} />
      {!data && !error && <LoadingState label="Calculando indicadores..." />}
      {error && <ErrorState message={error} retry={loadDashboard} />}
      {data && (
        <>
          <section className="metric-grid" aria-label="Indicadores do inventário">
            <article><span>Ativos cadastrados</span><strong>{data.summary.total_assets}</strong><small>{formatCurrency(data.summary.total_purchase_value)} em patrimônio</small></article>
            <article><span>Empréstimos ativos</span><strong>{data.summary.active_loans}</strong><small className={data.summary.overdue_loans ? 'danger-text' : ''}>{data.summary.overdue_loans} vencido(s)</small></article>
            <article><span>Manutenções abertas</span><strong>{data.summary.open_maintenances}</strong><small>{formatCurrency(data.summary.maintenance_cost_current_year)} no ano</small></article>
            <article><span>Garantias a vencer</span><strong>{data.summary.warranties_expiring_in_30_days}</strong><small>Próximos 30 dias</small></article>
          </section>

          <section className="dashboard-grid">
            <article className="panel">
              <div className="panel-heading"><div><p className="eyebrow">DISTRIBUIÇÃO</p><h2>Ativos por status</h2></div></div>
              {data.assets_by_status.length ? <DistributionBars data={data.assets_by_status} /> : <p className="muted">Cadastre ativos para visualizar a distribuição.</p>}
            </article>
            <article className="panel">
              <div className="panel-heading"><div><p className="eyebrow">CATEGORIAS</p><h2>Composição do parque</h2></div></div>
              {data.assets_by_category.length ? <DistributionBars data={data.assets_by_category} /> : <p className="muted">Nenhum dado disponível.</p>}
            </article>
          </section>

          <section className="panel movements-panel">
            <div className="panel-heading"><div><p className="eyebrow">HISTÓRICO</p><h2>Movimentações recentes</h2></div><small>Atualizado em {formatDateTime(data.generated_at)}</small></div>
            {data.latest_movements.length ? (
              <div className="activity-list">{data.latest_movements.map((movement) => (
                <article key={movement.id}><span className="activity-icon">↔</span><div><strong>{movement.asset_tag} · {movement.asset_name}</strong><p>{movement.movement_type_display} por {movement.performed_by ?? 'sistema'}</p></div><time>{formatDateTime(movement.created_at)}</time></article>
              ))}</div>
            ) : <p className="muted">As movimentações aparecerão aqui.</p>}
          </section>
        </>
      )}
    </>
  )
}
