export const API_URL: string =
  import.meta.env.PUBLIC_API_URL || 'https://backend-colegio-hdx7.onrender.com'

export const WS_URL: string =
  API_URL.replace(/^http/, 'ws') + '/ws'

export const SITE_NAME = 'Colegio Técnico Ciudad del Sol'
export const SITE_SHORT = 'C sol · SIE'
export const SITE_DESC =
  'Sistema de Información Estudiantil — Sogamoso, Boyacá, Colombia'
export const LOCALE = 'es-CO'
export const DEFAULT_THEME: 'dark' | 'light' = 'dark'
