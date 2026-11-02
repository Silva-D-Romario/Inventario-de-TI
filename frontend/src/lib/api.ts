const ACCESS_KEY = 'inventario.accessToken'
const REFRESH_KEY = 'inventario.refreshToken'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message)
  }
}

type RequestOptions = RequestInit & { retry?: boolean }

const messageFromPayload = (payload: unknown) => {
  if (!payload || typeof payload !== 'object') return 'Não foi possível concluir a operação.'
  const data = payload as Record<string, unknown>
  if (typeof data.detail === 'string') return data.detail
  const first = Object.values(data).at(0)
  if (typeof first === 'string') return first
  if (Array.isArray(first) && typeof first[0] === 'string') return first[0]
  return 'Verifique os dados informados e tente novamente.'
}

const parseResponse = async (response: Response) => {
  if (response.status === 204) return undefined
  const contentType = response.headers.get('content-type') ?? ''
  return contentType.includes('application/json') ? response.json() : response.text()
}

const refreshAccessToken = async () => {
  const refresh = localStorage.getItem(REFRESH_KEY)
  if (!refresh) return false

  const response = await fetch('/api/v1/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
  if (!response.ok) return false

  const tokens = (await response.json()) as { access: string; refresh?: string }
  localStorage.setItem(ACCESS_KEY, tokens.access)
  if (tokens.refresh) localStorage.setItem(REFRESH_KEY, tokens.refresh)
  return true
}

export const tokenStorage = {
  hasSession: () => Boolean(localStorage.getItem(REFRESH_KEY)),
  save: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { retry = true, headers, ...requestOptions } = options
  const access = localStorage.getItem(ACCESS_KEY)
  const response = await fetch(path, {
    ...requestOptions,
    headers: {
      ...(requestOptions.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
      ...headers,
    },
  })

  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return api<T>(path, { ...options, retry: false })
  }

  const payload = await parseResponse(response)
  if (!response.ok) throw new ApiError(messageFromPayload(payload), response.status, payload)
  return payload as T
}

export async function download(path: string, filename: string, retry = true): Promise<void> {
  const access = localStorage.getItem(ACCESS_KEY)
  const response = await fetch(path, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  })

  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return download(path, filename, false)
  }

  if (!response.ok) {
    const payload = await parseResponse(response)
    throw new ApiError(messageFromPayload(payload), response.status, payload)
  }

  const objectUrl = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}
