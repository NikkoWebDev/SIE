const API = (import.meta as any).env?.PUBLIC_API_URL?.replace(/\/+$/, '') || 'http://localhost:8000'

function getCookie(name: string): string {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? decodeURIComponent(match[2]) : ''
}

export function apiFetch(path: string, opts?: RequestInit): Promise<any> {
  const csrf = getCookie('csrf_token')
  const url = `${API}/${path.replace(/^\/+/, '')}`
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (csrf) headers['X-CSRF-Token'] = csrf
  const merged: RequestInit = {
    headers,
    credentials: 'include',
    ...opts,
  } as any
  if (merged.body && typeof merged.body === 'object' && !(merged.body instanceof FormData)) {
    merged.body = JSON.stringify(merged.body)
  }
  if ((merged.headers as any)['Content-Type'] === 'application/json' && merged.body instanceof FormData) {
    delete (merged.headers as any)['Content-Type']
  }
  return fetch(url, merged).then(r => {
    if (r.status === 401) { localStorage.clear(); window.location.href = '/login'; return {} }
    return r.json().catch(() => ({}))
  })
}

export function getToken(): string | null {
  return null // httpOnly cookie — browser sends it automatically
}

export function getUserId(): string | null {
  return localStorage.getItem('profile_id') || localStorage.getItem('userId')
}

export function getUserRole(): string {
  return (localStorage.getItem('userRole') || '').toUpperCase()
}

export function getUserName(): string {
  return localStorage.getItem('userName') || 'Usuario'
}

export function getUserGrade(): string {
  return localStorage.getItem('userGrade') || ''
}

export function authRedirect(): boolean {
  const hasSession = !!localStorage.getItem('userId')
  if (!hasSession) { window.location.href = '/login'; return false }
  return true
}

export function roleCheck(allowed: string[]): boolean {
  const role = getUserRole()
  if (!allowed.includes(role)) { window.location.href = '/'; return false }
  return true
}
