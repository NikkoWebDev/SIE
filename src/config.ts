export const API_URL: string =
  import.meta.env.PUBLIC_API_URL || 'http://localhost:8000'

export const WS_URL: string =
  API_URL.replace(/^http/, 'ws') + '/ws'

export const SITE_NAME = 'VYNTRA Academic'
export const SITE_SHORT = 'VYNTRA'
export const SITE_DESC =
  'Plataforma académica inteligente — Sogamoso, Boyacá, Colombia'
export const LOCALE = 'es-CO'
export const DEFAULT_THEME: 'dark' | 'light' = 'dark'
