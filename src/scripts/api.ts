const API_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.PUBLIC_API_URL) ||
  'https://backend-colegio-hdx7.onrender.com'

export function getApiUrl(): string {
  return API_URL
}

export function authHeaders(): Record<string, string> {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = 'Bearer ' + token
  return h
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const url = API_URL.replace(/\/+$/, '') + '/' + path.replace(/^\/+/, '')
  const merged: RequestInit = {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  }
  const res = await fetch(url, merged)
  if (res.status === 401) {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('userRole')
    localStorage.removeItem('userName')
    localStorage.removeItem('userId')
    window.location.href = '/login'
  }
  return res
}
