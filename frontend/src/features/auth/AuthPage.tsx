import { type FormEvent, useState } from 'react'

import { ApiError } from '../../lib/api'
import { useAuth } from './AuthContext'

export function AuthPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    const form = new FormData(event.currentTarget)

    try {
      if (mode === 'login') {
        await login({
          username: String(form.get('username')),
          password: String(form.get('password')),
        })
      } else {
        await register({
          username: String(form.get('username')),
          email: String(form.get('email')),
          first_name: String(form.get('first_name')),
          last_name: String(form.get('last_name')),
          password: String(form.get('password')),
          password_confirmation: String(form.get('password_confirmation')),
        })
      }
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Não foi possível entrar.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <div className="brand"><span className="brand-mark">IT</span> Inventário de TI</div>
        <div>
          <p className="eyebrow light">GESTÃO DE ATIVOS</p>
          <h1>Controle claro para toda a infraestrutura.</h1>
          <p>Patrimônio, responsáveis, empréstimos e manutenções em um único lugar.</p>
        </div>
        <p className="auth-footnote">API Django · auditoria · relatórios · alertas</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <p className="eyebrow">{mode === 'login' ? 'ACESSO SEGURO' : 'NOVA CONTA'}</p>
          <h2>{mode === 'login' ? 'Entre no sistema' : 'Crie sua conta'}</h2>
          <p>{mode === 'login' ? 'Use suas credenciais para acessar o inventário.' : 'Novas contas entram com perfil de consulta.'}</p>

          <form onSubmit={submit}>
            {mode === 'register' && (
              <div className="form-grid two-columns">
                <label>Nome<input name="first_name" autoComplete="given-name" required /></label>
                <label>Sobrenome<input name="last_name" autoComplete="family-name" required /></label>
              </div>
            )}
            <label>Usuário<input name="username" autoComplete="username" required /></label>
            {mode === 'register' && <label>E-mail<input name="email" type="email" autoComplete="email" required /></label>}
            <label>Senha<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required /></label>
            {mode === 'register' && <label>Confirmar senha<input name="password_confirmation" type="password" autoComplete="new-password" required /></label>}
            {error && <p className="form-message error" role="alert">{error}</p>}
            <button className="primary-button" disabled={submitting}>{submitting ? 'Aguarde...' : mode === 'login' ? 'Entrar' : 'Criar conta'}</button>
          </form>

          <button className="text-button mode-switch" type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? 'Ainda não tenho conta' : 'Já tenho uma conta'}
          </button>
        </div>
      </section>
    </main>
  )
}
