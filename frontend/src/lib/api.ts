// Single place that talks to the backend and unwraps its response envelope
// ({success, status, status_code, data, error} — see backend/README.md).
// Every feature's useQuery/useMutation calls through here, never fetch()
// directly, so the envelope is only unwrapped once, in one place.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface ApiSuccessEnvelope<T> {
  success: true
  status: string
  status_code: number
  data: T
}

interface ApiErrorEnvelope {
  success: false
  status: string
  status_code: number
  data: unknown
  error: { message: string }
}

type ApiEnvelope<T> = ApiSuccessEnvelope<T> | ApiErrorEnvelope

// A minimal structural check on the parsed JSON before it's trusted as
// ApiEnvelope<T> - catches a malformed/unexpected body (e.g. a proxy or
// gateway response that isn't our envelope shape) instead of an unchecked
// `as` letting a bad shape flow silently into every caller.
function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  if (
    typeof v.success !== 'boolean' ||
    typeof v.status !== 'string' ||
    typeof v.status_code !== 'number'
  ) {
    return false
  }
  if (v.success === false) {
    return (
      typeof v.error === 'object' &&
      v.error !== null &&
      typeof (v.error as Record<string, unknown>).message === 'string'
    )
  }
  return 'data' in v
}

export class ApiRequestError extends Error {
  readonly statusCode: number

  constructor(message: string, statusCode: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.statusCode = statusCode
  }
}

// Backend requires this header on all requests except health and docs.
// The value must match the backend's REQUEST_ID_SECRET.
const REQUEST_ID_SECRET = import.meta.env.VITE_REQUEST_ID_SECRET || ''

// Single source of truth for where the session token lives in
// localStorage - authContext.tsx imports this rather than duplicating the
// key, so the two can never drift apart.
export const AUTH_TOKEN_STORAGE_KEY = 'prepwise_token'

function getStoredAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

let unauthorizedHandler: (() => void) | null = null


export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler
}


function isAuthEndpoint(path: string): boolean {
  return path.startsWith('/auth/')
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  const token = getStoredAuthToken()

  let response: Response
  try {
    const isFormData = init?.body instanceof FormData
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        'X-Request-ID': REQUEST_ID_SECRET,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    })
  } catch {
    // fetch() itself rejects for a network-level failure (backend
    // unreachable, DNS, CORS)
    throw new ApiRequestError(
      'Could not reach the server. Please check your connection and try again.',
      0
    )
  }

  if (response.status === 401 && !isAuthEndpoint(path)) {
    unauthorizedHandler?.()
  }
  return response
}

const UNEXPECTED_RESPONSE_MESSAGE =
  'The server returned an unexpected response. Please try again.'


async function parseEnvelope<T>(response: Response): Promise<ApiEnvelope<T>> {
  let parsed: unknown
  try {
    parsed = await response.json()
  } catch {
    throw new ApiRequestError(UNEXPECTED_RESPONSE_MESSAGE, response.status)
  }
  if (!isApiEnvelope(parsed)) {
    throw new ApiRequestError(UNEXPECTED_RESPONSE_MESSAGE, response.status)
  }
  return parsed as ApiEnvelope<T>
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const body = await parseEnvelope<T>(await send(path, init))

  if (!body.success) {
    throw new ApiRequestError(body.error.message, body.status_code)
  }

  return body.data
}


async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await send(path, init)
  if (response.ok) return response.blob()

  const body = await parseEnvelope<never>(response)
  throw new ApiRequestError(
    body.success ? UNEXPECTED_RESPONSE_MESSAGE : body.error.message,
    response.status
  )
}

export const api = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string, payload: unknown): Promise<T> =>
    request<T>(path, { method: 'POST', body: JSON.stringify(payload) }),
  patch: <T>(path: string, payload: unknown): Promise<T> =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: <T>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData): Promise<T> =>
    request<T>(path, { method: 'POST', body: formData }),
  postForBlob: (path: string, payload: unknown, signal?: AbortSignal): Promise<Blob> =>
    requestBlob(path, { method: 'POST', body: JSON.stringify(payload), signal }),
}
