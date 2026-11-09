import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Asset, AssetStatus, Category, Sector } from '../../lib/types'
import { AssetForm } from './AssetForm'

const assetFormMocks = vi.hoisted(() => ({ api: vi.fn() }))

vi.mock('../../lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../../lib/api')>()
  return { ...original, api: assetFormMocks.api }
})

const categories: Category[] = [
  { id: 1, name: 'Impressora', description: '', is_active: true },
]
const sectors: Sector[] = [
  { id: 2, name: 'Administrativo', location: '', is_active: true },
]
const statuses: AssetStatus[] = [
  { id: 3, name: 'Em manutenção', code: 'maintenance', color: '#f59e0b', is_active: true },
  { id: 4, name: 'Disponível', code: 'available', color: '#22c55e', is_active: true },
]
const asset: Asset = {
  id: 10,
  public_id: 'asset-public-id',
  asset_tag: 'PAT-DEMO-003',
  name: 'Impressora HP LaserJet Pro',
  category: 1,
  category_name: 'Impressora',
  sector: 2,
  sector_name: 'Administrativo',
  status: 3,
  status_name: 'Em manutenção',
  status_color: '#f59e0b',
  responsible: null,
  responsible_name: null,
  qr_code_url: '/qr-code/',
  serial_number: 'DEMO-HP-M428-003',
  manufacturer: 'HP',
  model: 'LaserJet Pro M428',
  acquisition_date: '2026-05-12',
  purchase_value: '2850.00',
  notes: 'Registro demonstrativo.',
  created_by_username: 'romario.tech',
  created_at: '2026-11-01T10:00:00Z',
  updated_at: '2026-11-01T10:00:00Z',
}

describe('AssetForm', () => {
  beforeEach(() => assetFormMocks.api.mockReset().mockResolvedValue(undefined))

  it('edita o status sem enviar o setor desabilitado como NaN', async () => {
    const user = userEvent.setup()
    const onSaved = vi.fn()
    render(
      <AssetForm
        asset={asset}
        categories={categories}
        sectors={sectors}
        statuses={statuses}
        onCancel={vi.fn()}
        onSaved={onSaved}
      />,
    )

    await user.selectOptions(screen.getByLabelText('Status'), '4')
    await user.click(screen.getByRole('button', { name: 'Salvar ativo' }))

    await waitFor(() => expect(assetFormMocks.api).toHaveBeenCalledOnce())
    const [, options] = assetFormMocks.api.mock.calls[0]
    const payload = JSON.parse(options.body as string) as Record<string, unknown>

    expect(assetFormMocks.api).toHaveBeenCalledWith('/api/v1/inventory/assets/10/', {
      method: 'PATCH',
      body: expect.any(String),
    })
    expect(payload.category).toBe(1)
    expect(payload.status).toBe(4)
    expect(payload).not.toHaveProperty('sector')
    expect(onSaved).toHaveBeenCalledOnce()
  })
})
