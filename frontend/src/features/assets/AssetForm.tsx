import { type FormEvent, useState } from 'react'

import { ApiError, api } from '../../lib/api'
import type { Asset, AssetStatus, Category, Sector } from '../../lib/types'

interface AssetFormProps {
  asset: Asset | null
  categories: Category[]
  sectors: Sector[]
  statuses: AssetStatus[]
  onCancel: () => void
  onSaved: () => void
}

export function AssetForm({ asset, categories, sectors, statuses, onCancel, onSaved }: AssetFormProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const payload = Object.fromEntries(form.entries()) as Record<string, string>
    payload.category = String(Number(payload.category))
    payload.sector = String(Number(payload.sector))
    payload.status = String(Number(payload.status))
    if (!payload.purchase_value) delete payload.purchase_value
    if (!payload.acquisition_date) delete payload.acquisition_date

    setSubmitting(true)
    setError('')
    try {
      await api(`/api/v1/inventory/assets/${asset ? `${asset.id}/` : ''}`, {
        method: asset ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível salvar o ativo.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onCancel() }}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="asset-form-title">
        <div className="modal-heading"><div><p className="eyebrow">{asset ? 'EDIÇÃO' : 'NOVO REGISTRO'}</p><h2 id="asset-form-title">{asset ? 'Editar ativo' : 'Cadastrar ativo'}</h2></div><button className="icon-button" onClick={onCancel} aria-label="Fechar">×</button></div>
        <form className="form-grid" onSubmit={submit}>
          <label>Patrimônio<input name="asset_tag" defaultValue={asset?.asset_tag} placeholder="PAT-001" required /></label>
          <label>Nome<input name="name" defaultValue={asset?.name} placeholder="Notebook Dell Latitude" required /></label>
          <label>Categoria<select name="category" defaultValue={asset?.category} required><option value="">Selecione</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Setor<select name="sector" defaultValue={asset?.sector} disabled={Boolean(asset)} required><option value="">Selecione</option>{sectors.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>{asset && <small>Use a transferência para trocar o setor.</small>}</label>
          <label>Status<select name="status" defaultValue={asset?.status} required><option value="">Selecione</option>{statuses.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Número de série<input name="serial_number" defaultValue={asset?.serial_number ?? ''} /></label>
          <label>Fabricante<input name="manufacturer" defaultValue={asset?.manufacturer} /></label>
          <label>Modelo<input name="model" defaultValue={asset?.model} /></label>
          <label>Data de aquisição<input name="acquisition_date" type="date" defaultValue={asset?.acquisition_date ?? ''} /></label>
          <label>Valor de compra<input name="purchase_value" type="number" min="0" step="0.01" defaultValue={asset?.purchase_value ?? ''} /></label>
          <label className="full-width">Observações<textarea name="notes" rows={3} defaultValue={asset?.notes} /></label>
          {error && <p className="form-message error full-width">{error}</p>}
          <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onCancel}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Salvando...' : 'Salvar ativo'}</button></div>
        </form>
      </section>
    </div>
  )
}
