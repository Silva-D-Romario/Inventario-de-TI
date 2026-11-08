import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../lib/api'
import { AuthPage } from './AuthPage'

const authMocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
}))

vi.mock('./AuthContext', () => ({
  useAuth: () => authMocks,
}))

describe('AuthPage', () => {
  beforeEach(() => {
    authMocks.login.mockReset()
    authMocks.register.mockReset()
  })

  it('envia as credenciais no login', async () => {
    const user = userEvent.setup()
    render(<AuthPage />)

    await user.type(screen.getByLabelText('Usuário'), 'romario')
    await user.type(screen.getByLabelText('Senha'), 'senha-segura')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(authMocks.login).toHaveBeenCalledWith({
      username: 'romario',
      password: 'senha-segura',
    })
  })

  it('alterna para cadastro e envia todos os dados', async () => {
    const user = userEvent.setup()
    render(<AuthPage />)

    await user.click(screen.getByRole('button', { name: 'Ainda não tenho conta' }))
    await user.type(screen.getByLabelText('Nome'), 'Romário')
    await user.type(screen.getByLabelText('Sobrenome'), 'Silva')
    await user.type(screen.getByLabelText('Usuário'), 'romario')
    await user.type(screen.getByLabelText('E-mail'), 'romario@example.com')
    await user.type(screen.getByLabelText('Senha'), 'senha-segura')
    await user.type(screen.getByLabelText('Confirmar senha'), 'senha-segura')
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))

    expect(authMocks.register).toHaveBeenCalledWith({
      username: 'romario',
      email: 'romario@example.com',
      first_name: 'Romário',
      last_name: 'Silva',
      password: 'senha-segura',
      password_confirmation: 'senha-segura',
    })
  })

  it('mostra a mensagem retornada pela API', async () => {
    authMocks.login.mockRejectedValue(new ApiError('Credenciais inválidas.', 401))
    const user = userEvent.setup()
    render(<AuthPage />)

    await user.type(screen.getByLabelText('Usuário'), 'romario')
    await user.type(screen.getByLabelText('Senha'), 'incorreta')
    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Credenciais inválidas.')
  })
})
