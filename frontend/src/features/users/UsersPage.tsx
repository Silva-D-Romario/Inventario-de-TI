import { useCallback, useEffect, useMemo, useState } from 'react'

import { ErrorState, LoadingState } from '../../components/common/Feedback'
import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import type { Page, User, UserRole } from '../../lib/types'
import { useAuth } from '../auth/AuthContext'

const roleLabels: Record<UserRole, string> = {
  USER: 'Usuário',
  TECHNICIAN: 'Técnico',
  ADMIN: 'Administrador',
}

function UserAccessRow({ account, isCurrent, onSaved }: { account: User; isCurrent: boolean; onSaved: () => void }) {
  const [role, setRole] = useState(account.role)
  const [active, setActive] = useState(account.is_active)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await api(`/api/v1/auth/users/${account.id}/access/`, {
        method: 'PATCH',
        body: JSON.stringify({ role, is_active: active }),
      })
      onSaved()
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível atualizar o acesso.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr>
      <td><strong>{account.full_name || account.username}</strong><span>@{account.username}</span><small>{account.email}</small></td>
      <td><select aria-label={`Perfil de ${account.username}`} value={role} onChange={(event) => setRole(event.target.value as UserRole)} disabled={isCurrent}>{Object.entries(roleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></td>
      <td><label className="inline-toggle"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} disabled={isCurrent} /> {active ? 'Ativo' : 'Inativo'}</label></td>
      <td><div className="user-access-action">{isCurrent ? <small>Sua conta</small> : <button className="secondary-button compact" onClick={save} disabled={saving}>{saving ? 'Salvando...' : 'Salvar acesso'}</button>}{error ? <small className="inline-error">{error}</small> : null}</div></td>
    </tr>
  )
}

export function UsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<User[] | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const response = await api<Page<User>>('/api/v1/auth/users/?page_size=100')
      setUsers(response.results)
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível carregar os usuários.')
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const filteredUsers = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('pt-BR')
    if (!query) return users ?? []
    return (users ?? []).filter((account) => `${account.full_name} ${account.username} ${account.email}`.toLocaleLowerCase('pt-BR').includes(query))
  }, [search, users])

  return (
    <>
      <PageHeader eyebrow="ADMINISTRAÇÃO" title="Usuários e acessos" description="Defina perfis e controle quais contas podem acessar o sistema." action={<button className="secondary-button" onClick={load}>Atualizar</button>} />
      <section className="filter-bar user-filter"><label>Buscar<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nome, usuário ou e-mail" /></label><div className="filter-summary"><strong>{filteredUsers.length}</strong><span>usuário(s)</span></div></section>
      {!users && !error ? <LoadingState label="Carregando usuários..." /> : null}
      {error ? <ErrorState message={error} retry={load} /> : null}
      {users ? <div className="table-card"><table><thead><tr><th>Conta</th><th>Perfil</th><th>Status</th><th aria-label="Ações" /></tr></thead><tbody>{filteredUsers.map((account) => <UserAccessRow key={`${account.id}-${account.role}-${account.is_active}`} account={account} isCurrent={account.id === user?.id} onSaved={load} />)}</tbody></table></div> : null}
    </>
  )
}
