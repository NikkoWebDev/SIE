// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Dynamic Chart.js Loader
// Replaces static import in DashboardShell with lazy loading.
// Eliminates setTimeout-based race conditions.
// ════════════════════════════════════════════════════════════════

interface ChartJSModule {
  Chart: typeof import('chart.js').Chart
  registerables: typeof import('chart.js').registerables
}

let chartModulePromise: Promise<ChartJSModule> | null = null
let chartReady = false

const pendingResolvers: Array<(chart: ChartJSModule) => void> = []

function resolveAll(module: ChartJSModule) {
  chartReady = true
  if (typeof window !== 'undefined') {
    window.Chart = module.Chart as any
    window.dispatchEvent(new CustomEvent('chart:ready', { detail: module.Chart }))
  }
  pendingResolvers.forEach((resolve) => resolve(module))
  pendingResolvers.length = 0
}

export function getChartJS(): Promise<ChartJSModule> {
  if (chartReady && chartModulePromise) return chartModulePromise
  if (chartModulePromise) return chartModulePromise

  chartModulePromise = import('chart.js')
    .then((mod) => {
      mod.Chart.register(...mod.registerables)
      const module: ChartJSModule = { Chart: mod.Chart, registerables: mod.registerables }
      resolveAll(module)
      return module
    })
    .catch((err) => {
      chartModulePromise = null
      throw err
    })

  return chartModulePromise
}

// For pages that need Chart synchronously (backward compat with setTimeout retry pattern)
export function getChartWhenReady(): Promise<typeof import('chart.js').Chart> {
  return new Promise((resolve) => {
    if (typeof window !== 'undefined' && window.Chart) {
      resolve(window.Chart as any)
      return
    }
    const handler = (e: Event) => {
      window.removeEventListener('chart:ready', handler)
      resolve((e as CustomEvent).detail)
    }
    window.addEventListener('chart:ready', handler, { once: true })
    // Also try loading if not already loading
    getChartJS().catch(() => {})
  })
}

export function destroyChart(canvas: HTMLCanvasElement | null): void {
  if (!canvas) return
  try {
    const existing = (window.Chart as any)?.getChart?.(canvas)
    if (existing) existing.destroy()
  } catch (_) { /* noop */ }
}

// Expose on window (once)
if (typeof window !== 'undefined' && !window.__chartsExposed) {
  window.__chartsExposed = true
  window.getChartJS = getChartJS as any
  window.getChartWhenReady = getChartWhenReady
}
