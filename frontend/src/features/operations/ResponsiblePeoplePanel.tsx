import { type FormEvent, useState } from 'react'

import { Modal } from '../../components/common/Modal'
import { ApiError, api } from '../../lib/api'
import type { ResponsiblePerson, Sector } from '../../lib/types'

interface Props {
  people: ResponsiblePerson[]
  sectors: Sector[]
  canEdit: boolean
  canDelete: boolean
  onChanged: () => void
}

export function ResponsiblePeoplePanel({ people, sectors, canEdit, canDelete, onChanged }: Props) {
  const [editing, setEditing] = useState<ResponsiblePerson | null | undefined>(undefined)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setError('')
    try {
      await api(`/api/v1/inventory/responsible-people/${editing ? `${editing.id}/` : ''}`, {
        method: editing ? 'PATCH' : 'POST',
        body: JSON.stringify({
          name: data.get('name'),
          email: data.get('email'),
          employee_id: data.get('employee_id') || null,
          phone: data.get('phone'),
          sector: Number(data.get('sector')),
          is_active: data.get('is_active') === 'on',
        }),
      })
      setEditing(undefined)
      onChanged()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível salvar o responsável.')
    }
  }

  const remove = async (person: ResponsiblePerson) => {
    if (!window.confirm(`Excluir ${person.name}?`)) return
    try {
      await api(`/api/v1/inventory/responsible-people/${person.id}/`, { method: 'DELETE' })
      onChanged()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível excluir o responsável.')
    }
  }

  return (
    <article className="panel people-panel">
      <div className="panel-heading"><div><p className="eyebrow">PESSOAS</p><h2>Responsáveis</h2></div><div className="heading-actions"><span className="count-badge">{people.length}</span>{canEdit && <button className="secondary-button compact" onClick={() => setEditing(null)}>+ Adicionar</button>}</div></div>
      {error && <p className="form-message error">{error}</p>}
      {!people.length ? <p className="muted">Cadastre quem poderá receber os ativos.</p> : <div className="compact-list">{people.map((person) => (
        <article key={person.id}><div><strong>{person.name}</strong><span>{person.email} · {person.sector_name}</span><small>{person.employee_id || person.phone || 'Sem identificação complementar'}</small></div><div className="row-actions">{canEdit && <button className="text-button" onClick={() => setEditing(person)}>Editar</button>}{canDelete && <button className="text-button danger" onClick={() => remove(person)}>Excluir</button>}</div></article>
      ))}</div>}
      {editing !== undefined && (
        <Modal eyebrow="RESPONSÁVEL" title={editing ? 'Editar responsável' : 'Cadastrar responsável'} onClose={() => setEditing(undefined)}>
          <form key={editing?.id ?? 'new'} className="form-grid" onSubmit={submit}>
            <label>Nome<input name="name" defaultValue={editing?.name} required /></label>
            <label>E-mail<input name="email" type="email" defaultValue={editing?.email} required /></label>
            <label>Matrícula<input name="employee_id" defaultValue={editing?.employee_id ?? ''} /></label>
            <label>Telefone<input name="phone" defaultValue={editing?.phone} /></label>
            <label>Setor<select name="sector" defaultValue={editing?.sector} required><option value="">Selecione</option>{sectors.map((sector) => <option key={sector.id} value={sector.id}>{sector.name}</option>)}</select></label>
            <label className="checkbox-field"><input name="is_active" type="checkbox" defaultChecked={editing?.is_active ?? true} /> Ativo</label>
            {error && <p className="form-message error full-width">{error}</p>}
            <div className="form-actions full-width"><button type="button" className="secondary-button" onClick={() => setEditing(undefined)}>Cancelar</button><button className="primary-button">Salvar responsável</button></div>
          </form>
        </Modal>
      )}
    </article>
  )
}
