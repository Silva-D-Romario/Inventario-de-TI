import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, tokenStorage } from './api'

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('envia o token de acesso e devolve a resposta JSON', async () => {
    tokenStorage.save('access-token', 'refresh-token')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ id: 1, name: 'Notebook' }),
    )

    await expect(api('/api/v1/assets/1/')).resolves.toEqual({ id: 1, name: 'Notebook' })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/assets/1/',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer access-token' }),
      }),
    )
  })

  it('renova o token expirado e repete a requisicao', async () => {
    tokenStorage.save('expired-token', 'refresh-token')
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({ detail: 'Token expirado.' }, 401))
      .mockResolvedValueOnce(jsonResponse({ access: 'new-access-token' }))
      .mockResolvedValueOnce(jsonResponse({ count: 3 }))

    await expect(api('/api/v1/assets/')).resolves.toEqual({ count: 3 })
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/auth/token/refresh/',
      expect.objectContaining({ body: JSON.stringify({ refresh: 'refresh-token' }) }),
    )
    expect(localStorage.getItem('inventario.accessToken')).toBe('new-access-token')
  })

  it('transforma erros da API em ApiError legivel', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ email: ['Informe um e-mail válido.'] }, 400),
    )

    const request = api('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify({ email: 'invalido' }),
      retry: false,
    })

    await expect(request).rejects.toMatchObject({
      message: 'Informe um e-mail válido.',
      status: 400,
    })
  })
})
