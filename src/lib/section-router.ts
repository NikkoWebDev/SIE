// ════════════════════════════════════════════════════════════════
// VYNTRA SOLARIS — Unified Section Router
// Replaces duplicated showSection() logic across dashboard pages.
// Supports lazy loading, force reload, and inaccessible alerts.
// ════════════════════════════════════════════════════════════════

interface SectionRouterConfig {
  titles: Record<string, string>
  subtitles: Record<string, string>
  loaders: Record<string, () => Promise<void> | void>
  onNavigate?: (section: string) => void
  startSection?: string
  defaultSection?: string
  titleSelector?: string   // defaults to '.topbar-heading'
  subtitleSelector?: string // defaults to '.topbar-subtitle'
}

export function createSectionRouter(config: SectionRouterConfig) {
  const {
    titles,
    subtitles,
    loaders,
    onNavigate,
    startSection = 'inicio',
    defaultSection = 'inicio',
    titleSelector = '.topbar-heading',
    subtitleSelector = '.topbar-subtitle',
  } = config

  const loaded = new Set<string>()
  let currentSection = startSection

  const showSection = (id: string | undefined, forceReload = false) => {
    const section = id || defaultSection
    currentSection = section

    document.querySelectorAll('[id^="sec-"]').forEach((s) => {
      const el = s as HTMLElement
      el.style.display = 'none'
      el.classList.remove('section-enter')
    })

    const sec = document.getElementById(`sec-${section}`)
    if (sec) {
      sec.style.display = ''
      sec.classList.remove('hidden')
      sec.classList.add('section-enter')
    }

    const titleEl = document.querySelector(titleSelector)
    const subEl = document.querySelector(subtitleSelector)
    if (titleEl) titleEl.textContent = titles[section] || section
    if (subEl) subEl.textContent = subtitles[section] || ''

    window.dispatchEvent(new CustomEvent('vyntra:navigate', { detail: { section } }))

    onNavigate?.(section)

    const loader = loaders[section]
    if (loader && (forceReload || !loaded.has(section))) {
      loaded.add(section)
      try {
        const result = loader()
        if (result instanceof Promise) {
          result.catch((err) => {
            console.error(`[section-router] Error loading "${section}":`, err)
            window.VyntraToast?.error(`Error al cargar la sección "${titles[section] || section}"`)
          })
        }
      } catch (err) {
        console.error(`[section-router] Error loading "${section}":`, err)
      }
    }
  }

  const reloadSection = (id: string) => {
    loaded.delete(id)
    showSection(id, true)
  }

  return { showSection, reloadSection, getCurrentSection: () => currentSection }
}

if (typeof window !== 'undefined' && !window.__sectionRouterExposed) {
  window.__sectionRouterExposed = true
  window.createSectionRouter = createSectionRouter
}
