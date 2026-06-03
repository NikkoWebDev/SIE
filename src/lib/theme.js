export function setTheme(dark) {
  document.documentElement.classList.toggle('dark', dark)
  localStorage.setItem('vyntra-theme', dark ? 'dark' : 'light')
}

export function getTheme() {
  const stored = localStorage.getItem('vyntra-theme')
  if (stored) return stored === 'dark'
  return window.matchMedia('(prefers-color-scheme:dark)').matches
}

export function initTheme() {
  setTheme(getTheme())
  const toggles = document.querySelectorAll('[data-theme-toggle]')
  toggles.forEach(btn => {
    btn.addEventListener('click', () => setTheme(!document.documentElement.classList.contains('dark')))
  })
}
