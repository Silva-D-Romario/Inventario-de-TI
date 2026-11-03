import { type FormEvent, useState } from 'react'

import { Modal } from '../../../components/common/Modal'
import { ApiError, api } from '../../../lib/api'
import type { Asset, AssetCost, Maintenance, ResponsiblePerson, Sector, Warranty } from '../../../lib/types'

interface FormCallbacks {
  onClose: () => void
  onSaved: () => void
}

const today = () => new Date().toISOString().slice(0, 10)

function FormError({ message }: { message: string }) {
  return message ? <p className="form-message error full-width">{message}</p> : null
}

export function TransferForm({ asset, sectors, people, onClose, onSaved }: FormCallbacks & { asset: Asset; sectors: Sector[]; people: ResponsiblePerson[] }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [destinationSector, setDestinationSector] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await api(`/api/v1/inventory/assets/${asset.id}/transfer/`, {
        method: 'POST',
        body: JSON.stringify({
          to_sector: Number(data.get('to_sector')),
          responsible: data.get('responsible') ? Number(data.get('responsible')) : null,
          notes: String(data.get('notes')),
        }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível transferir o ativo.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="MOVIMENTAÇÃO" title={`Transferir ${asset.asset_tag}`} onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label>Setor de destino<select name="to_sector" value={destinationSector} onChange={(event) => setDestinationSector(event.target.value)} required><option value="">Selecione</option>{sectors.filter((sector) => sector.is_active).map((sector) => <option key={sector.id} value={sector.id}>{sector.name}</option>)}</select></label>
        <label>Responsável<select key={destinationSector} name="responsible" defaultValue="" disabled={!destinationSector}><option value="">Sem responsável</option>{people.filter((person) => person.is_active && person.sector === Number(destinationSector)).map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>
        <label className="full-width">Observações<textarea name="notes" rows={4} placeholder="Motivo e informações da transferência" /></label>
        <FormError message={error} />
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Transferindo...' : 'Confirmar transferência'}</button></div>
      </form>
    </Modal>
  )
}

export function WarrantyForm({ asset, warranty, onClose, onSaved }: FormCallbacks & { asset: Asset; warranty: Warranty | null }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await api(`/api/v1/inventory/warranties/${warranty ? `${warranty.id}/` : ''}`, {
        method: warranty ? 'PATCH' : 'POST',
        body: JSON.stringify({
          asset: asset.id,
          provider: data.get('provider'),
          contract_number: data.get('contract_number'),
          start_date: data.get('start_date'),
          end_date: data.get('end_date'),
          coverage_notes: data.get('coverage_notes'),
        }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível salvar a garantia.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="PROTEÇÃO" title={warranty ? 'Editar garantia' : 'Cadastrar garantia'} onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label>Fornecedor<input name="provider" defaultValue={warranty?.provider} required /></label>
        <label>Contrato<input name="contract_number" defaultValue={warranty?.contract_number} /></label>
        <label>Data inicial<input name="start_date" type="date" defaultValue={warranty?.start_date} required /></label>
        <label>Data final<input name="end_date" type="date" defaultValue={warranty?.end_date} required /></label>
        <label className="full-width">Cobertura<textarea name="coverage_notes" rows={4} defaultValue={warranty?.coverage_notes} /></label>
        <FormError message={error} />
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Salvando...' : 'Salvar garantia'}</button></div>
      </form>
    </Modal>
  )
}

export function CostForm({ asset, cost, maintenances, onClose, onSaved }: FormCallbacks & { asset: Asset; cost: AssetCost | null; maintenances: Maintenance[] }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await api(`/api/v1/inventory/costs/${cost ? `${cost.id}/` : ''}`, {
        method: cost ? 'PATCH' : 'POST',
        body: JSON.stringify({
          asset: asset.id,
          maintenance: data.get('maintenance') ? Number(data.get('maintenance')) : null,
          cost_type: data.get('cost_type'),
          amount: data.get('amount'),
          occurred_on: data.get('occurred_on'),
          description: data.get('description'),
        }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível salvar o custo.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="FINANCEIRO" title={cost ? 'Editar custo' : 'Registrar custo'} onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label>Tipo<select name="cost_type" defaultValue={cost?.cost_type ?? 'OTHER'} required><option value="PURCHASE">Compra</option><option value="MAINTENANCE">Manutenção</option><option value="LICENSE">Licença</option><option value="OTHER">Outro</option></select></label>
        <label>Valor<input name="amount" type="number" min="0.01" step="0.01" defaultValue={cost?.amount} required /></label>
        <label>Data<input name="occurred_on" type="date" max={today()} defaultValue={cost?.occurred_on ?? today()} required /></label>
        <label>Manutenção relacionada<select name="maintenance" defaultValue={cost?.maintenance ?? ''}><option value="">Nenhuma</option>{maintenances.map((maintenance) => <option key={maintenance.id} value={maintenance.id}>{maintenance.maintenance_type_display} · {maintenance.started_at}</option>)}</select></label>
        <label className="full-width">Descrição<textarea name="description" rows={4} defaultValue={cost?.description} required /></label>
        <FormError message={error} />
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Salvando...' : 'Salvar custo'}</button></div>
      </form>
    </Modal>
  )
}

export function AttachmentForm({ asset, maintenances, onClose, onSaved }: FormCallbacks & { asset: Asset; maintenances: Maintenance[] }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const source = new FormData(event.currentTarget)
    const body = new FormData()
    body.set('asset', String(asset.id))
    body.set('description', String(source.get('description')))
    if (source.get('maintenance')) body.set('maintenance', String(source.get('maintenance')))
    const file = source.get('file')
    if (file instanceof File) body.set('file', file)

    setSubmitting(true)
    setError('')
    try {
      await api('/api/v1/inventory/attachments/', { method: 'POST', body })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível enviar o anexo.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="DOCUMENTOS" title="Adicionar anexo" onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label className="full-width">Arquivo<input name="file" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" required /><small>PDF ou imagem, com no máximo 5 MB.</small></label>
        <label>Manutenção relacionada<select name="maintenance" defaultValue=""><option value="">Nenhuma</option>{maintenances.map((maintenance) => <option key={maintenance.id} value={maintenance.id}>{maintenance.maintenance_type_display} · {maintenance.started_at}</option>)}</select></label>
        <label>Descrição<input name="description" placeholder="Nota fiscal, laudo, foto..." /></label>
        <FormError message={error} />
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Enviando...' : 'Enviar anexo'}</button></div>
      </form>
    </Modal>
  )
}
