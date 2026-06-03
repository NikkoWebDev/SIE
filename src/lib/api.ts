// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Unified API Client
// ════════════════════════════════════════════════════════════════

const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000'

function apiUrl(): string {
  return (API_BASE as string).replace(/\/+$/, '')
}

function getToken(): string {
  try {
    return localStorage.getItem('access_token') || ''
  } catch {
    return ''
  }
}

function authHeaders(contentType = 'application/json'): Record<string, string> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': contentType,
  }
  // Send Authorization header if token exists (for cookie auth, backend reads cookie as fallback)
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    typeof localStorage !== 'undefined' && localStorage.clear()
    window.location.href = '/login'
    throw new Error('Sesión expirada')
  }
  if (res.status === 429) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Demasiadas solicitudes. Intenta de nuevo en un minuto.')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || err.mensaje || err.error || `Error ${res.status}`)
  }
  return res.json()
}

export const api = {
  get: async <T>(path: string): Promise<T> => {
    const res = await fetch(`${apiUrl()}${path}`, {
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },

  post: async <T>(path: string, body?: unknown): Promise<T> => {
    const res = await fetch(`${apiUrl()}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  put: async <T>(path: string, body?: unknown): Promise<T> => {
    const res = await fetch(`${apiUrl()}${path}`, {
      method: 'PUT',
      headers: authHeaders(),
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  patch: async <T>(path: string, body?: unknown): Promise<T> => {
    const res = await fetch(`${apiUrl()}${path}`, {
      method: 'PATCH',
      headers: authHeaders(),
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  delete: async <T>(path: string): Promise<T> => {
    const res = await fetch(`${apiUrl()}${path}`, {
      method: 'DELETE',
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },

  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const token = getToken()
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    const res = await fetch(`${apiUrl()}${path}`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: formData,
    })
    return handleResponse<T>(res)
  },

  get raw() {
    return apiUrl()
  },
}
