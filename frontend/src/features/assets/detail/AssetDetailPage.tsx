import { useCallback, useEffect, useMemo, useState } from 'react'

import { navigation } from '../../../app/navigation'
import { ErrorState, LoadingState } from '../../../components/common/Feedback'
import { PageHeader } from '../../../components/common/PageHeader'
import { ApiError, api, download } from '../../../lib/api'
import { formatCurrency, formatDate, formatDateTime } from '../../../lib/format'
import type { Asset, AssetAttachment, AssetCost, AssetMovement, Maintenance, Page, ResponsiblePerson, Sector, Warranty } from '../../../lib/types'
import { useAuth } from '../../auth/AuthContext'
import { AssetQrCard } from './AssetQrCard'
import { AttachmentForm, CostForm, TransferForm, WarrantyForm } from './AssetDetailForms'

interface AssetDetailData {
  asset: Asset
  warranties: Warranty[]
  costs: AssetCost[]
  attachments: AssetAttachment[]
  movements: AssetMovement[]
  maintenances: Maintenance[]
  sectors: Sector[]
  people: ResponsiblePerson[]
}

type Editor =
  | { kind: 'transfer' }
  | { kind: 'warranty'; value: Warranty | null }
  | { kind: 'cost'; value: AssetCost | null }
  | { kind: 'attachment' }
  | null

const page = <T,>(path: string) => api<Page<T>>(`${path}${path.includes('?') ? '&' : '?'}page_size=100`).then((response) => response.results)

export function AssetDetailPage({ assetId }: { assetId: number }) {
  const { user } = useAuth()
  const canOperate = user?.role === 'TECHNICIAN' || user?.role === 'ADMIN'
  const canDelete = user?.role === 'ADMIN'
  const [data, setData] = useState<AssetDetailData | null>(null)
  const [editor, setEditor] = useState<Editor>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [asset, warranties, costs, attachments, movements, maintenances, sectors, people] = await Promise.all([
        api<Asset>(`/api/v1/inventory/assets/${assetId}/`),
        page<Warranty>(`/api/v1/inventory/warranties/?asset=${assetId}&ordering=-end_date`),
        page<AssetCost>(`/api/v1/inventory/costs/?asset=${assetId}&ordering=-occurred_on`),
        page<AssetAttachment>(`/api/v1/inventory/attachments/?asset=${assetId}&ordering=-created_at`),
        page<AssetMovement>(`/api/v1/inventory/movements/?asset=${assetId}&ordering=-created_at`),
        page<Maintenance>(`/api/v1/inventory/maintenances/?asset=${assetId}&ordering=-started_at`),
        page<Sector>('/api/v1/inventory/sectors/?ordering=name'),
        page<ResponsiblePerson>('/api/v1/inventory/responsible-people/?ordering=name'),
      ])
      setData({ asset, warranties, costs, attachments, movements, maintenances, sectors, people })
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar os detalhes do ativo.')
    }
  }, [assetId])

  useEffect(() => { void load() }, [load])

  const totalCost = useMemo(() => data?.costs.reduce((total, cost) => total + Number(cost.amount), 0) ?? 0, [data?.costs])

  const saved = async () => {
    setEditor(null)
    await load()
  }

  const remove = async (path: string, label: string) => {
    if (!window.confirm(`Excluir ${label}?`)) return
    try {
      await api(path, { method: 'DELETE' })
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível excluir o registro.')
    }
  }

  if (!data && !error) return <LoadingState label="Carregando detalhes do ativo..." />
  if (!data) return <ErrorState message={error} retry={load} />

  const { asset, warranties, costs, attachments, movements, maintenances, sectors, people } = data

  return (
    <>
      <PageHeader
        eyebrow="DETALHES DO ATIVO"
        title={`${asset.asset_tag} · ${asset.name}`}
        description={`${asset.category_name} em ${asset.sector_name}${asset.responsible_name ? `, sob responsabilidade de ${asset.responsible_name}` : ''}.`}
        action={<div className="header-actions"><button className="secondary-button" onClick={() => navigation.go('assets')}>← Voltar</button>{canOperate && <button className="primary-button" onClick={() => setEditor({ kind: 'transfer' })}>Transferir ativo</button>}</div>}
      />
      {error && <p className="form-message error detail-message">{error}</p>}

      <section className="asset-overview">
        <article className="panel asset-summary">
          <div className="asset-summary-heading"><div><p className="eyebrow">PATRIMÔNIO</p><h2>Informações gerais</h2></div><span className="status-pill"><i style={{ background: asset.status_color }} />{asset.status_name}</span></div>
          <dl>
            <div><dt>Fabricante e modelo</dt><dd>{[asset.manufacturer, asset.model].filter(Boolean).join(' · ') || 'Não informado'}</dd></div>
            <div><dt>Número de série</dt><dd>{asset.serial_number || 'Não informado'}</dd></div>
            <div><dt>Aquisição</dt><dd>{formatDate(asset.acquisition_date)}</dd></div>
            <div><dt>Valor de compra</dt><dd>{formatCurrency(asset.purchase_value)}</dd></div>
            <div><dt>Custos registrados</dt><dd>{formatCurrency(String(totalCost))}</dd></div>
            <div><dt>Identificador público</dt><dd className="code-value">{asset.public_id}</dd></div>
          </dl>
          {asset.notes && <p className="asset-notes">{asset.notes}</p>}
        </article>
        <AssetQrCard asset={asset} />
      </section>

      <section className="asset-resource-grid">
        <article className="panel resource-card">
          <div className="panel-heading"><div><p className="eyebrow">PROTEÇÃO</p><h2>Garantias</h2></div>{canOperate && <button className="secondary-button compact" onClick={() => setEditor({ kind: 'warranty', value: null })}>+ Adicionar</button>}</div>
          {!warranties.length ? <p className="muted">Nenhuma garantia cadastrada.</p> : <div className="detail-list">{warranties.map((warranty) => <article key={warranty.id}><div><strong>{warranty.provider}</strong><span>{formatDate(warranty.start_date)} até {formatDate(warranty.end_date)}</span><small>{warranty.contract_number || warranty.coverage_notes || 'Sem detalhes adicionais'}</small></div><div className="detail-actions"><span className={`status-pill ${warranty.is_active ? 'success' : ''}`}>{warranty.is_active ? 'Ativa' : 'Encerrada'}</span>{canOperate && <button className="text-button" onClick={() => setEditor({ kind: 'warranty', value: warranty })}>Editar</button>}{canDelete && <button className="text-button danger" onClick={() => remove(`/api/v1/inventory/warranties/${warranty.id}/`, `a garantia de ${warranty.provider}`)}>Excluir</button>}</div></article>)}</div>}
        </article>

        <article className="panel resource-card">
          <div className="panel-heading"><div><p className="eyebrow">FINANCEIRO</p><h2>Custos</h2></div>{canOperate && <button className="secondary-button compact" onClick={() => setEditor({ kind: 'cost', value: null })}>+ Adicionar</button>}</div>
          {!costs.length ? <p className="muted">Nenhum custo registrado.</p> : <div className="detail-list">{costs.map((cost) => <article key={cost.id}><div><strong>{cost.cost_type_display} · {formatCurrency(cost.amount)}</strong><span>{formatDate(cost.occurred_on)}</span><small>{cost.description}</small></div><div className="detail-actions">{canOperate && <button className="text-button" onClick={() => setEditor({ kind: 'cost', value: cost })}>Editar</button>}{canDelete && <button className="text-button danger" onClick={() => remove(`/api/v1/inventory/costs/${cost.id}/`, `o custo de ${formatCurrency(cost.amount)}`)}>Excluir</button>}</div></article>)}</div>}
        </article>

        <article className="panel resource-card">
          <div className="panel-heading"><div><p className="eyebrow">DOCUMENTOS</p><h2>Anexos</h2></div>{canOperate && <button className="secondary-button compact" onClick={() => setEditor({ kind: 'attachment' })}>+ Adicionar</button>}</div>
          {!attachments.length ? <p className="muted">Nenhum documento anexado.</p> : <div className="detail-list">{attachments.map((attachment) => <article key={attachment.id}><div><strong>{attachment.file_name}</strong><span>{attachment.description || 'Sem descrição'}</span><small>{formatDateTime(attachment.created_at)} · {attachment.uploaded_by_username || 'Sistema'}</small></div><div className="detail-actions"><button className="text-button" onClick={() => download(attachment.download_url, attachment.file_name)}>Baixar</button>{canDelete && <button className="text-button danger" onClick={() => remove(`/api/v1/inventory/attachments/${attachment.id}/`, attachment.file_name)}>Excluir</button>}</div></article>)}</div>}
        </article>
      </section>

      <article className="panel movements-panel">
        <div className="panel-heading"><div><p className="eyebrow">RASTREABILIDADE</p><h2>Histórico de movimentações</h2></div><span className="count-badge">{movements.length}</span></div>
        {!movements.length ? <p className="muted">Nenhuma movimentação registrada.</p> : <div className="movement-timeline">{movements.map((movement) => <article key={movement.id}><span className="timeline-marker">↔</span><div><strong>{movement.movement_type_display}</strong><p>{[movement.from_sector_name, movement.to_sector_name].filter(Boolean).join(' → ') || movement.responsible_name || 'Atualização operacional'}</p>{movement.notes && <small>{movement.notes}</small>}</div><time>{formatDateTime(movement.created_at)}<small>{movement.performed_by_username || 'Sistema'}</small></time></article>)}</div>}
      </article>

      {editor?.kind === 'transfer' && <TransferForm asset={asset} sectors={sectors} people={people} onClose={() => setEditor(null)} onSaved={saved} />}
      {editor?.kind === 'warranty' && <WarrantyForm asset={asset} warranty={editor.value} onClose={() => setEditor(null)} onSaved={saved} />}
      {editor?.kind === 'cost' && <CostForm asset={asset} cost={editor.value} maintenances={maintenances} onClose={() => setEditor(null)} onSaved={saved} />}
      {editor?.kind === 'attachment' && <AttachmentForm asset={asset} maintenances={maintenances} onClose={() => setEditor(null)} onSaved={saved} />}
    </>
  )
}
