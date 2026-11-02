import { type FormEvent, useState } from 'react'

import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, download } from '../../lib/api'
import { useAuth } from '../auth/AuthContext'

type ReportKind = 'assets' | 'costs' | 'maintenances'

const reportConfig: Record<ReportKind, { endpoint: string; filename: string }> = {
  assets: { endpoint: 'assets.csv', filename: 'ativos.csv' },
  costs: { endpoint: 'costs.csv', filename: 'custos.csv' },
  maintenances: { endpoint: 'maintenances.csv', filename: 'manutencoes.csv' },
}

export function ReportsPage() {
  const { user } = useAuth()
  const [downloading, setDownloading] = useState<ReportKind | null>(null)
  const [message, setMessage] = useState('')

  if (user?.role === 'USER') {
    return <section className="state-box error"><strong>Acesso restrito</strong><p>Somente técnicos e administradores podem exportar relatórios.</p></section>
  }

  const exportReport = async (kind: ReportKind, event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setDownloading(kind)
    setMessage('')
    const params = new URLSearchParams()
    new FormData(event.currentTarget).forEach((value, key) => { if (value) params.set(key, String(value)) })
    const config = reportConfig[kind]
    try {
      await download(`/api/v1/inventory/reports/${config.endpoint}?${params}`, config.filename)
      setMessage('Relatório gerado com sucesso.')
    } catch (caughtError) {
      setMessage(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível gerar o relatório.')
    } finally {
      setDownloading(null)
    }
  }

  return (
    <>
      <PageHeader eyebrow="EXPORTAÇÃO" title="Relatórios" description="Exporte dados filtrados em CSV compatível com Excel e LibreOffice." />
      {message && <p className={`form-message ${message.includes('sucesso') ? 'success' : 'error'} report-message`}>{message}</p>}
      <section className="report-grid">
        <article className="panel report-card"><div><span className="report-icon">▤</span><p className="eyebrow">PATRIMÔNIO</p><h2>Ativos</h2><p>Inventário com classificação, localização, responsável e valor de compra.</p></div><form onSubmit={(event) => exportReport('assets', event)}><div className="form-grid"><label>Aquisição inicial<input name="acquisition_from" type="date" /></label><label>Aquisição final<input name="acquisition_to" type="date" /></label></div><button className="primary-button" disabled={downloading !== null}>{downloading === 'assets' ? 'Gerando...' : 'Baixar ativos CSV'}</button></form></article>
        <article className="panel report-card"><div><span className="report-icon">R$</span><p className="eyebrow">FINANCEIRO</p><h2>Custos</h2><p>Despesas registradas por tipo, data e equipamento.</p></div><form onSubmit={(event) => exportReport('costs', event)}><div className="form-grid"><label>Data inicial<input name="occurred_from" type="date" /></label><label>Data final<input name="occurred_to" type="date" /></label></div><button className="primary-button" disabled={downloading !== null}>{downloading === 'costs' ? 'Gerando...' : 'Baixar custos CSV'}</button></form></article>
        <article className="panel report-card"><div><span className="report-icon">⚙</span><p className="eyebrow">SUPORTE</p><h2>Manutenções</h2><p>Histórico com tipo, status, prestador, datas e custo final.</p></div><form onSubmit={(event) => exportReport('maintenances', event)}><div className="form-grid"><label>Início do período<input name="started_from" type="date" /></label><label>Fim do período<input name="started_to" type="date" /></label><label>Tipo<select name="maintenance_type"><option value="">Todos</option><option value="PREVENTIVE">Preventiva</option><option value="CORRECTIVE">Corretiva</option></select></label><label>Status<select name="status"><option value="">Todos</option><option value="IN_PROGRESS">Em andamento</option><option value="COMPLETED">Concluída</option><option value="CANCELLED">Cancelada</option></select></label></div><button className="primary-button" disabled={downloading !== null}>{downloading === 'maintenances' ? 'Gerando...' : 'Baixar manutenções CSV'}</button></form></article>
      </section>
    </>
  )
}
