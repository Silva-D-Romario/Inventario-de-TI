import { type FormEvent, useState } from 'react'

import { PageHeader } from '../../components/common/PageHeader'
import { ApiError, api } from '../../lib/api'
import { useAuth } from '../auth/AuthContext'

export function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [profileMessage, setProfileMessage] = useState('')
  const [passwordMessage, setPasswordMessage] = useState('')

  if (!user) return null

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setSavingProfile(true)
    setProfileMessage('')
    try {
      await api('/api/v1/auth/me/', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: data.get('first_name'),
          last_name: data.get('last_name'),
          email: data.get('email'),
        }),
      })
      await refreshUser()
      setProfileMessage('Perfil atualizado com sucesso.')
    } catch (caughtError) {
      setProfileMessage(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível atualizar o perfil.')
    } finally {
      setSavingProfile(false)
    }
  }

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    setSavingPassword(true)
    setPasswordMessage('')
    try {
      await api('/api/v1/auth/password/', {
        method: 'POST',
        body: JSON.stringify({
          current_password: data.get('current_password'),
          new_password: data.get('new_password'),
          password_confirmation: data.get('password_confirmation'),
        }),
      })
      form.reset()
      setPasswordMessage('Senha alterada com sucesso.')
    } catch (caughtError) {
      setPasswordMessage(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível alterar a senha.')
    } finally {
      setSavingPassword(false)
    }
  }

  return (
    <>
      <PageHeader eyebrow="CONTA" title="Meu perfil" description="Atualize seus dados pessoais e proteja o acesso à sua conta." />
      <section className="settings-grid">
        <article className="panel settings-card">
          <div><p className="eyebrow">DADOS PESSOAIS</p><h2>Informações da conta</h2><p>Seu usuário e perfil de acesso são controlados pelo administrador.</p></div>
          <form className="form-grid" onSubmit={saveProfile}>
            <label>Usuário<input value={user.username} disabled /></label>
            <label>Perfil<input value={user.role_display} disabled /></label>
            <label>Nome<input name="first_name" defaultValue={user.first_name} required /></label>
            <label>Sobrenome<input name="last_name" defaultValue={user.last_name} /></label>
            <label className="full-width">E-mail<input name="email" type="email" defaultValue={user.email} required /></label>
            {profileMessage ? <p className={`form-message full-width ${profileMessage.includes('sucesso') ? 'success' : 'error'}`} aria-live="polite">{profileMessage}</p> : null}
            <div className="form-actions full-width"><button className="primary-button" disabled={savingProfile}>{savingProfile ? 'Salvando...' : 'Salvar perfil'}</button></div>
          </form>
        </article>

        <article className="panel settings-card">
          <div><p className="eyebrow">SEGURANÇA</p><h2>Alterar senha</h2><p>Use uma senha forte e diferente das utilizadas em outros serviços.</p></div>
          <form className="form-grid" onSubmit={changePassword}>
            <label className="full-width">Senha atual<input name="current_password" type="password" autoComplete="current-password" required /></label>
            <label>Nova senha<input name="new_password" type="password" autoComplete="new-password" minLength={8} required /></label>
            <label>Confirmar nova senha<input name="password_confirmation" type="password" autoComplete="new-password" minLength={8} required /></label>
            {passwordMessage ? <p className={`form-message full-width ${passwordMessage.includes('sucesso') ? 'success' : 'error'}`} aria-live="polite">{passwordMessage}</p> : null}
            <div className="form-actions full-width"><button className="primary-button" disabled={savingPassword}>{savingPassword ? 'Alterando...' : 'Alterar senha'}</button></div>
          </form>
        </article>
      </section>
    </>
  )
}
