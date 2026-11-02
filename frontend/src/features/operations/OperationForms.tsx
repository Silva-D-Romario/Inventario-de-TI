import { type FormEvent, useState } from 'react'

import { Modal } from '../../components/common/Modal'
import { ApiError, api } from '../../lib/api'
import type { Asset, Loan, Maintenance, ResponsiblePerson } from '../../lib/types'

interface SharedFormProps {
  assets: Asset[]
  onClose: () => void
  onSaved: () => void
}

const today = () => new Date().toISOString().slice(0, 10)

export function LoanForm({ assets, people, onClose, onSaved }: SharedFormProps & { people: ResponsiblePerson[] }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await api('/api/v1/inventory/loans/', {
        method: 'POST',
        body: JSON.stringify({
          asset: Number(data.get('asset')),
          borrower: Number(data.get('borrower')),
          loaned_at: String(data.get('loaned_at')),
          expected_return_date: String(data.get('expected_return_date')),
          notes: String(data.get('notes')),
        }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível registrar o empréstimo.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="MOVIMENTAÇÃO" title="Registrar empréstimo" onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label>Ativo<select name="asset" required><option value="">Selecione</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_tag} · {asset.name}</option>)}</select></label>
        <label>Responsável<select name="borrower" required><option value="">Selecione</option>{people.filter((person) => person.is_active).map((person) => <option key={person.id} value={person.id}>{person.name} · {person.sector_name}</option>)}</select></label>
        <label>Data do empréstimo<input name="loaned_at" type="date" max={today()} defaultValue={today()} required /></label>
        <label>Devolução prevista<input name="expected_return_date" type="date" min={today()} required /></label>
        <label className="full-width">Observações<textarea name="notes" rows={3} placeholder="Finalidade ou cuidados com o equipamento" /></label>
        {error && <p className="form-message error full-width">{error}</p>}
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Registrando...' : 'Registrar empréstimo'}</button></div>
      </form>
    </Modal>
  )
}

export function MaintenanceForm({ assets, onClose, onSaved }: SharedFormProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      await api('/api/v1/inventory/maintenances/', {
        method: 'POST',
        body: JSON.stringify({
          asset: Number(data.get('asset')),
          maintenance_type: data.get('maintenance_type'),
          started_at: data.get('started_at'),
          provider: data.get('provider'),
          description: data.get('description'),
        }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível iniciar a manutenção.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="SUPORTE" title="Iniciar manutenção" onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        <label>Ativo<select name="asset" required><option value="">Selecione</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_tag} · {asset.name}</option>)}</select></label>
        <label>Tipo<select name="maintenance_type" required><option value="CORRECTIVE">Corretiva</option><option value="PREVENTIVE">Preventiva</option></select></label>
        <label>Data de início<input name="started_at" type="date" max={today()} defaultValue={today()} required /></label>
        <label>Prestador<input name="provider" placeholder="Equipe interna ou fornecedor" /></label>
        <label className="full-width">Descrição<textarea name="description" rows={4} placeholder="Defeito, diagnóstico ou serviço previsto" required /></label>
        {error && <p className="form-message error full-width">{error}</p>}
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Cancelar</button><button className="primary-button" disabled={submitting}>{submitting ? 'Iniciando...' : 'Iniciar manutenção'}</button></div>
      </form>
    </Modal>
  )
}

type FinishTarget =
  | { kind: 'return'; loan: Loan }
  | { kind: 'complete'; maintenance: Maintenance }
  | { kind: 'cancel'; maintenance: Maintenance }

export function FinishOperationForm({ target, onClose, onSaved }: { target: FinishTarget; onClose: () => void; onSaved: () => void }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const isReturn = target.kind === 'return'
  const isComplete = target.kind === 'complete'
  const title = isReturn ? `Devolver ${target.loan.asset_tag}` : isComplete ? `Concluir ${target.maintenance.asset_tag}` : `Cancelar ${target.maintenance.asset_tag}`

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const path = isReturn
      ? `/api/v1/inventory/loans/${target.loan.id}/return/`
      : `/api/v1/inventory/maintenances/${target.maintenance.id}/${target.kind}/`
    const payload = isReturn
      ? { notes: String(data.get('notes')) }
      : { resolution_notes: String(data.get('notes')), cost: isComplete ? Number(data.get('cost')) : 0 }
    setSubmitting(true)
    setError('')
    try {
      await api(path, { method: 'POST', body: JSON.stringify(payload) })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível concluir a operação.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal eyebrow="CONFIRMAÇÃO" title={title} onClose={onClose}>
      <form className="form-grid" onSubmit={submit}>
        {isComplete && <label className="full-width">Custo final<input name="cost" type="number" min="0" step="0.01" defaultValue="0.00" required /></label>}
        <label className="full-width">{isReturn ? 'Observações da devolução' : 'Notas de resolução'}<textarea name="notes" rows={4} placeholder="Registre as condições e informações relevantes" /></label>
        {error && <p className="form-message error full-width">{error}</p>}
        <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={onClose}>Voltar</button><button className={target.kind === 'cancel' ? 'danger-button' : 'primary-button'} disabled={submitting}>{submitting ? 'Salvando...' : 'Confirmar operação'}</button></div>
      </form>
    </Modal>
  )
}

export type { FinishTarget }
