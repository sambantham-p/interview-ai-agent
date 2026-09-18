import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiRequestError, AUTH_TOKEN_STORAGE_KEY } from './api'

function mockFetchOnce(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      json: () => Promise.resolve(body),
    })
  )
}

describe('REQUEST_ID_SECRET fallback', () => {
  it('falls back to an empty string when VITE_REQUEST_ID_SECRET is unset at import time', async () => {
    // REQUEST_ID_SECRET is a module-level constant evaluated once at
    // import - .env sets a real value for every other test in this file,
    // so exercising the fallback branch needs a fresh module instance
    // with the env var cleared beforehand.
    const original = import.meta.env.VITE_REQUEST_ID_SECRET
    // import.meta.env's values are typed `any` (Vite's default
    // ImportMetaEnv), so overriding one here for the test needs no cast.
    import.meta.env.VITE_REQUEST_ID_SECRET = ''
    vi.resetModules()

    try {
      const freshApi = await import('./api')
      mockFetchOnce({ success: true, status: 'ok', status_code: 200, data: {} })
      await freshApi.api.get('/health')

      const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(init.headers['X-Request-ID']).toBe('')
    } finally {
      import.meta.env.VITE_REQUEST_ID_SECRET = original
      vi.resetModules()
    }
  })
})

describe('api.get', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches an Authorization header when a token is stored', async () => {
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'a-real-token')
    mockFetchOnce({ success: true, status: 'ok', status_code: 200, data: { ok: true } })

    await api.get('/auth/me')

    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers.Authorization).toBe('Bearer a-real-token')
  })

  it('omits the Authorization header when no token is stored', async () => {
    mockFetchOnce({ success: true, status: 'ok', status_code: 200, data: { ok: true } })

    await api.get('/health')

    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers.Authorization).toBeUndefined()
  })

  it('sends a JSON body on POST', async () => {
    mockFetchOnce({ success: true, status: 'ok', status_code: 200, data: { id: 1 } })

    await api.post('/auth/login', { email: 'alex@prepwise.ai', password: 'secret' })

    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ email: 'alex@prepwise.ai', password: 'secret' }))
  })

  it('omits the Authorization header when reading the stored token throws', async () => {
    const getItemSpy = vi
      .spyOn(Storage.prototype, 'getItem')
      .mockImplementation(() => {
        throw new Error('storage blocked')
      })
    mockFetchOnce({ success: true, status: 'ok', status_code: 200, data: { ok: true } })

    await api.get('/health')

    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(init.headers.Authorization).toBeUndefined()
    getItemSpy.mockRestore()
  })

  it('throws ApiRequestError with the envelope message and status on failure', async () => {
    mockFetchOnce({
      success: false,
      status: 'error',
      status_code: 401,
      data: null,
      error: { message: 'Invalid or expired session token.' },
    })

    await expect(api.get('/auth/me')).rejects.toMatchObject({
      message: 'Invalid or expired session token.',
      statusCode: 401,
    })
    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(ApiRequestError)
  })

  it('throws a clear ApiRequestError when the server is unreachable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    )

    await expect(api.get('/health')).rejects.toMatchObject({
      message: 'Could not reach the server. Please check your connection and try again.',
      statusCode: 0,
    })
    await expect(api.get('/health')).rejects.toBeInstanceOf(ApiRequestError)
  })

  it('throws a clear ApiRequestError when the parsed body is not an ApiEnvelope shape', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 502,
        json: () => Promise.resolve({ not: 'an envelope' }),
      })
    )

    await expect(api.get('/health')).rejects.toMatchObject({
      message: 'The server returned an unexpected response. Please try again.',
      statusCode: 502,
    })
    await expect(api.get('/health')).rejects.toBeInstanceOf(ApiRequestError)
  })

  it('throws a clear ApiRequestError when the response body is not valid JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        status: 502,
        json: () => Promise.reject(new SyntaxError('Unexpected end of JSON input')),
      })
    )

    await expect(api.get('/health')).rejects.toMatchObject({
      message: 'The server returned an unexpected response. Please try again.',
      statusCode: 502,
    })
    await expect(api.get('/health')).rejects.toBeInstanceOf(ApiRequestError)
  })
})
