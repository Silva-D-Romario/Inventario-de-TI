import { useCallback, useEffect, useState } from 'react'

import { EmptyState, ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { useAuth } from '../auth/AuthContext'
import { ApiError, api } from '../../lib/api'
import { formatCurrency, formatDate } from '../../lib/format'
import type { Asset, AssetStatus, Category, Page, Sector } from '../../lib/types'
import { AssetForm } from './AssetForm'
import { navigation } from '../../app/navigation'

export function AssetsPage() {
  const { user } = useAuth()
  const canEdit = user?.role === 'TECHNICIAN' || user?.role === 'ADMIN'
  const canDelete = user?.role === 'ADMIN'
  const [assets, setAssets] = useState<Page<Asset> | null>(null)
  const [references, setReferences] = useState<{ categories: Category[]; sectors: Sector[]; statuses: AssetStatus[] }>({ categories: [], sectors: [], statuses: [] })
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Asset | null | undefined>(undefined)
  const [error, setError] = useState('')

  const loadReferences = useCallback(async () => {
    const [categories, sectors, statuses] = await Promise.all([
      api<Page<Category>>('/api/v1/inventory/categories/?page_size=100'),
      api<Page<Sector>>('/api/v1/inventory/sectors/?page_size=100'),
      api<Page<AssetStatus>>('/api/v1/inventory/statuses/?page_size=100'),
    ])
    setReferences({ categories: categories.results, sectors: sectors.results, statuses: statuses.results })
  }, [])

  const loadAssets = useCallback(async () => {
    setError('')
    const params = new URLSearchParams({ page: String(page), ordering: 'asset_tag' })
    if (search) params.set('search', search)
    if (status) params.set('status', status)
    try {
      setAssets(await api<Page<Asset>>(`/api/v1/inventory/assets/?${params}`))
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar os ativos.')
    }
  }, [page, search, status])

  useEffect(() => { void loadReferences().catch(() => setError('Não foi possível carregar os cadastros auxiliares.')) }, [loadReferences])
  useEffect(() => { void loadAssets() }, [loadAssets])

  const remove = async (asset: Asset) => {
    if (!window.confirm(`Excluir o ativo ${asset.asset_tag}?`)) return
    try {
      await api(`/api/v1/inventory/assets/${asset.id}/`, { method: 'DELETE' })
      await loadAssets()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível excluir o ativo.')
    }
  }

  const closeAndReload = async () => { setEditing(undefined); await loadAssets() }

  return (
    <>
      <PageHeader eyebrow="PATRIMÔNIO" title="Ativos de TI" description="Consulte e mantenha os equipamentos registrados." action={canEdit && <button className="primary-button" onClick={() => setEditing(null)}>+ Novo ativo</button>} />
      <section className="filter-bar">
        <label>Buscar<input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Patrimônio, nome, fabricante..." /></label>
        <label>Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">Todos</option>{references.statuses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <button className="secondary-button" onClick={() => { setSearch(''); setStatus(''); setPage(1) }}>Limpar filtros</button>
      </section>
      {!assets && !error && <LoadingState label="Carregando ativos..." />}
      {error && <ErrorState message={error} retry={loadAssets} />}
      {assets && !assets.results.length && <EmptyState title="Nenhum ativo encontrado" description="Ajuste os filtros ou cadastre o primeiro equipamento." />}
      {assets && assets.results.length > 0 && (
        <>
          <div className="table-card"><table><thead><tr><th>Ativo</th><th>Categoria</th><th>Setor</th><th>Status</th><th>Valor</th><th aria-label="Ações" /></tr></thead><tbody>{assets.results.map((asset) => (
            <tr key={asset.id}>
              <td><strong>{asset.asset_tag}</strong><span>{asset.name}</span><small>{[asset.manufacturer, asset.model].filter(Boolean).join(' · ') || asset.serial_number || 'Sem detalhes técnicos'}</small></td>
              <td>{asset.category_name}</td><td>{asset.sector_name}</td>
              <td><span className="status-pill"><i style={{ background: asset.status_color }} />{asset.status_name}</span></td>
              <td><span>{formatCurrency(asset.purchase_value)}</span><small>{formatDate(asset.acquisition_date)}</small></td>
              <td><div className="row-actions"><button className="text-button" onClick={() => navigation.asset(asset.id)}>Detalhes</button>{canEdit && <button className="text-button" onClick={() => setEditing(asset)}>Editar</button>}{canDelete && <button className="text-button danger" onClick={() => remove(asset)}>Excluir</button>}</div></td>
            </tr>
          ))}</tbody></table></div>
          <div className="pagination"><button className="secondary-button" disabled={!assets.previous} onClick={() => setPage((value) => value - 1)}>Anterior</button><span>Página {page} · {assets.count} registro(s)</span><button className="secondary-button" disabled={!assets.next} onClick={() => setPage((value) => value + 1)}>Próxima</button></div>
        </>
      )}
      {editing !== undefined && <AssetForm asset={editing} categories={references.categories} sectors={references.sectors} statuses={references.statuses} onCancel={() => setEditing(undefined)} onSaved={closeAndReload} />}
    </>
  )
}
