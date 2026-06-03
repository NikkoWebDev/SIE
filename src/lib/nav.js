export function initNavigation(titles, subs) {
  window.showSection = function(id) {
    document.querySelectorAll('[id^="sec-"]').forEach(s => { s.style.display = 'none' })
    const sec = document.getElementById('sec-' + id)
    if (sec) sec.style.display = ''
    const t = document.querySelector('.topbar h1')
    const s = document.querySelector('.topbar p')
    if (t) t.textContent = titles[id] || id
    if (s) s.textContent = subs[id] || ''
    window.dispatchEvent(new CustomEvent('vyntra:navigate', { detail: { section: id } }))
    if (id === 'notas') window.loadGrades && window.loadGrades()
    if (id === 'examenes') window.loadExams && window.loadExams()
  }

  document.querySelectorAll('[data-section-id]').forEach(btn => {
    btn.addEventListener('click', () => window.showSection(btn.getAttribute('data-section-id')))
  })

  document.querySelectorAll('[id^="sec-"]').forEach(s => {
    if (s.id !== 'sec-inicio') s.style.display = 'none'
  })
}

export function startClock() {
  setInterval(() => {
    const el = document.getElementById('live-clock')
    if (el) el.textContent = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }, 1000)
}
