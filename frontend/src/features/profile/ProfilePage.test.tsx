import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ProfilePage } from './ProfilePage'

const profileMocks = vi.hoisted(() => ({
  api: vi.fn(),
  refreshUser: vi.fn(),
  user: {
    id: 1,
    username: 'romario',
    email: 'romario@example.com',
    first_name: 'Romário',
    last_name: 'Silva',
    full_name: 'Romário Silva',
    role: 'ADMIN',
    role_display: 'Administrador',
    is_active: true,
  },
}))

vi.mock('../../lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../../lib/api')>()
  return { ...original, api: profileMocks.api }
})

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: profileMocks.user, refreshUser: profileMocks.refreshUser }),
}))

describe('ProfilePage', () => {
  beforeEach(() => {
    profileMocks.api.mockReset().mockResolvedValue(undefined)
    profileMocks.refreshUser.mockReset().mockResolvedValue(undefined)
  })

  it('atualiza os dados pessoais e recarrega o usuario', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    const email = screen.getByLabelText('E-mail')
    await user.clear(email)
    await user.type(email, 'novo@example.com')
    await user.click(screen.getByRole('button', { name: 'Salvar perfil' }))

    expect(profileMocks.api).toHaveBeenCalledWith('/api/v1/auth/me/', {
      method: 'PATCH',
      body: JSON.stringify({
        first_name: 'Romário',
        last_name: 'Silva',
        email: 'novo@example.com',
      }),
    })
    expect(profileMocks.refreshUser).toHaveBeenCalledOnce()
    expect(await screen.findByText('Perfil atualizado com sucesso.')).toBeVisible()
  })

  it('altera a senha e limpa os campos', async () => {
    const user = userEvent.setup()
    render(<ProfilePage />)

    await user.type(screen.getByLabelText('Senha atual'), 'senha-atual')
    await user.type(screen.getByLabelText('Nova senha'), 'nova-senha-segura')
    await user.type(screen.getByLabelText('Confirmar nova senha'), 'nova-senha-segura')
    await user.click(screen.getByRole('button', { name: 'Alterar senha' }))

    expect(profileMocks.api).toHaveBeenCalledWith('/api/v1/auth/password/', {
      method: 'POST',
      body: JSON.stringify({
        current_password: 'senha-atual',
        new_password: 'nova-senha-segura',
        password_confirmation: 'nova-senha-segura',
      }),
    })
    expect(await screen.findByText('Senha alterada com sucesso.')).toBeVisible()
    expect(screen.getByLabelText('Senha atual')).toHaveValue('')
  })
})
