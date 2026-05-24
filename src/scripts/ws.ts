const WS_URL: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.PUBLIC_API_URL
    ? (import.meta.env.PUBLIC_API_URL as string).replace(/^http/, 'ws')
    : 'wss://backend-colegio-hdx7.onrender.com') + '/ws'

type MessageHandler = (data: Record<string, unknown>) => void

export class WsClient {
  private ws: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private delay = 1000
  private maxDelay = 30000
  private handlers = new Map<string, Set<MessageHandler>>()
  private destroyed = false

  connect(): void {
    if (this.destroyed) return
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null
    if (!token) { this.schedule(); return }
    try {
      this.ws = new WebSocket(WS_URL + '?token=' + encodeURIComponent(token))
    } catch {
      this.schedule()
      return
    }
    this.ws.onopen = () => { this.delay = 1000 }
    this.ws.onmessage = (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data) as Record<string, unknown>
        const type = (msg.type || msg.kind) as string
        if (type && this.handlers.has(type)) {
          this.handlers.get(type)!.forEach(fn => fn(msg))
        }
        if (this.handlers.has('*')) {
          this.handlers.get('*')!.forEach(fn => fn(msg))
        }
      } catch { /* ignore malformed */ }
    }
    this.ws.onclose = () => { this.ws = null; this.schedule() }
    this.ws.onerror = () => { this.ws?.close() }
  }

  on(type: string, handler: MessageHandler): void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler)
  }

  off(type: string, handler: MessageHandler): void {
    this.handlers.get(type)?.delete(handler)
  }

  private schedule(): void {
    if (this.destroyed) return
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.reconnectTimer = setTimeout(() => {
      this.delay = Math.min(this.delay * 1.5, this.maxDelay)
      this.connect()
    }, this.delay)
  }

  disconnect(): void {
    this.destroyed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
    this.handlers.clear()
  }
}

let _instance: WsClient | null = null
export function getWs(): WsClient {
  if (!_instance) {
    _instance = new WsClient()
    _instance.connect()
  }
  return _instance
}
