import { type FormEvent, useCallback, useEffect, useState } from 'react'

import { ApiError, api } from '../../lib/api'
import type { Page } from '../../lib/types'

interface FieldDefinition {
  key: string
  label: string
  placeholder?: string
  type?: string
  required?: boolean
}

interface ReferenceItem {
  id: number
  name: string
  is_active: boolean
  [key: string]: unknown
}

interface ReferenceManagerProps {
  title: string
  endpoint: string
  fields: FieldDefinition[]
}

export function ReferenceManager({ title, endpoint, fields }: ReferenceManagerProps) {
  const [items, setItems] = useState<ReferenceItem[]>([])
  const [editing, setEditing] = useState<ReferenceItem | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const load = useCallback(async () => {
    const page = await api<Page<ReferenceItem>>(`/api/v1/inventory/${endpoint}/?page_size=100`)
    setItems(page.results)
  }, [endpoint])

  useEffect(() => { void load().catch((caughtError) => setError(caughtError instanceof ApiError ? caughtError.message : 'Erro ao carregar cadastros.')) }, [load])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setSuccess('')
    const form = event.currentTarget
    const payload = Object.fromEntries(new FormData(form).entries())
    payload.is_active = String((form.elements.namedItem('is_active') as HTMLInputElement).checked)
    try {
      await api(`/api/v1/inventory/${endpoint}/${editing ? `${editing.id}/` : ''}`, {
        method: editing ? 'PATCH' : 'POST',
        body: JSON.stringify({ ...payload, is_active: payload.is_active === 'true' }),
      })
      setSuccess(editing ? 'Cadastro atualizado.' : 'Cadastro criado.')
      setEditing(null)
      form.reset()
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível salvar.')
    }
  }

  const remove = async (item: ReferenceItem) => {
    if (!window.confirm(`Excluir ${item.name}?`)) return
    try {
      await api(`/api/v1/inventory/${endpoint}/${item.id}/`, { method: 'DELETE' })
      await load()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível excluir.')
    }
  }

  return (
    <article className="panel reference-panel">
      <div className="panel-heading"><h2>{title}</h2><span className="count-badge">{items.length}</span></div>
      <form key={editing?.id ?? 'new'} className="reference-form" onSubmit={submit}>
        {fields.map((field) => <label key={field.key}>{field.label}<input name={field.key} type={field.type ?? 'text'} placeholder={field.placeholder} defaultValue={editing ? String(editing[field.key] ?? '') : ''} required={field.required} /></label>)}
        <label className="checkbox-field"><input name="is_active" type="checkbox" defaultChecked={editing?.is_active ?? true} /> Ativo</label>
        {error && <p className="form-message error full-width">{error}</p>}
        {success && <p className="form-message success full-width">{success}</p>}
        <div className="form-actions full-width">{editing && <button type="button" className="secondary-button" onClick={() => setEditing(null)}>Cancelar</button>}<button className="primary-button">{editing ? 'Salvar alterações' : `Adicionar ${title.toLowerCase()}`}</button></div>
      </form>
      <div className="reference-list">{items.map((item) => (
        <div key={item.id}><div><strong>{item.name}</strong><small>{item.is_active ? 'Ativo' : 'Inativo'}</small></div><div className="row-actions"><button className="text-button" onClick={() => { setEditing(item); setError(''); setSuccess('') }}>Editar</button><button className="text-button danger" onClick={() => remove(item)}>Excluir</button></div></div>
      ))}</div>
    </article>
  )
}
