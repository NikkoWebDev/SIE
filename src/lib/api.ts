// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Unified API Client
// Replaces inline window.vfetch with a proper, reusable client.
// ════════════════════════════════════════════════════════════════

const API_URL = (import.meta.env.PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

export function createTimeoutSignal(ms = 15000): { signal: AbortSignal; clear: () => void } {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), ms)
  return { signal: ctrl.signal, clear: () => clearTimeout(timer) }
}

function handle401(): never {
  try { localStorage.clear() } catch (_) { /* noop */ }
  if (typeof window !== 'undefined') {
    window.VyntraToast?.error('Sesión expirada. Redirigiendo al inicio...')
    setTimeout(() => { window.location.href = '/login' }, 1500)
  }
  throw new Error('Sesión expirada')
}

export async function apiFetch(path: string, opts: RequestInit = {}): Promise<any> {
  const url = `${API_URL}${path.startsWith('/') ? '' : '/'}${path}`
  const { signal: timeoutSignal, clear } = createTimeoutSignal(opts.signal ? 0 : 15000)

  const isFormData = opts.body instanceof FormData
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string> || {}) }
  if (!isFormData) headers['Content-Type'] = 'application/json'

  const signal = opts.signal || timeoutSignal
  const merged: RequestInit = {
    ...opts,
    credentials: 'include',
    headers,
    signal,
  }

  try {
    const res = await fetch(url, merged)
    clear()
    if (res.status === 401) handle401()
    // try json, fallback to raw response for non-json endpoints
    const text = await res.text()
    try { return JSON.parse(text) } catch { return { _raw: text, ok: res.ok, status: res.status } }
  } catch (e: any) {
    clear()
    if (e.name === 'AbortError' && !opts.signal) {
      throw new Error('La solicitud excedió el tiempo de espera.')
    }
    throw e
  }
}

export function postJson(path: string, body: unknown, opts: RequestInit = {}): Promise<any> {
  return apiFetch(path, { ...opts, method: 'POST', body: JSON.stringify(body) })
}

export function postForm(path: string, formData: FormData, opts: RequestInit = {}): Promise<any> {
  return apiFetch(path, { ...opts, method: 'POST', body: formData })
}

// ── Backward-compatible vfetch (same signature as original window.vfetch) ──
export function vfetch(baseUrl: string, path: string, opts: any = {}): Promise<Response> {
  const url = baseUrl.replace(/\/+$/, '') + '/' + path.replace(/^\/+/, '')
  const isFormData = opts.body instanceof FormData
  const headers: Record<string, string> = { ...(opts.headers || {}) }
  if (!isFormData) headers['Content-Type'] = 'application/json'

  const { signal, clear } = createTimeoutSignal(15000)
  const merged: RequestInit = {
    credentials: 'include',
    ...opts,
    headers,
    signal: opts.signal || signal,
  }

  return fetch(url, merged).then((r) => {
    clear()
    if (r.status === 401) handle401()
    return r
  }).catch((e) => {
    clear()
    throw e
  })
}

// Expose on window for backward compatibility (once)
if (typeof window !== 'undefined' && !window.__apiExposed) {
  window.__apiExposed = true
  window.apiFetch = apiFetch
  window.vfetch = vfetch
  window.createTimeoutSignal = createTimeoutSignal
}
