// VYNTRA Solaris — Shared Dashboard Library v1.0
;(function () {
  // ── Theme ──
  window.setVyntraTheme = function (dark) {
    document.documentElement.classList.toggle('dark', dark)
    try { localStorage.setItem('vyntra-theme', dark ? 'dark' : 'light') } catch (_) {}
  }

  // Initialize theme from storage or system preference
  try {
    var stored = localStorage.getItem('vyntra-theme')
    var prefersDark = window.matchMedia('(prefers-color-scheme:dark)').matches
    window.setVyntraTheme(stored === 'dark' || (!stored && prefersDark))
  } catch (_) {}

  // ── Section Navigation ──
  window.createShowSection = function (configs) {
    var titles = configs.titles || {}
    var subs = configs.subs || {}
    var onNavigate = configs.onNavigate || function () {}

    return function showSection(id) {
      document.querySelectorAll('[id^="sec-"]').forEach(function (s) {
        s.style.display = 'none'
      })
      var sec = document.getElementById('sec-' + id)
      if (sec) sec.style.display = ''

      var topTitle = document.querySelector('.topbar h1')
      var topSub = document.querySelector('.topbar p')
      if (topTitle) topTitle.textContent = titles[id] || id
      if (topSub) topSub.textContent = subs[id] || ''

      window.dispatchEvent(new CustomEvent('vyntra:navigate', { detail: { section: id } }))
      onNavigate(id)
    }
  }

  // ── API Fetch Helper ──
  window.vfetch = function (apiUrl, path, opts) {
    var token = null
    try { token = localStorage.getItem('access_token') } catch (_) {}
    var headers = Object.assign({ 'Authorization': 'Bearer ' + token }, opts && opts.headers)
    var options = Object.assign({}, opts, { headers: headers })
    return fetch(apiUrl + path, options).then(function (r) {
      if (r.status === 401) {
        try { localStorage.clear() } catch (_) {}
        window.location.href = '/login'
        throw new Error('Token expirado')
      }
      return r
    })
  }

  // ── Live Clock ──
  window.startVyntraClock = function (elementId) {
    function tick() {
      var el = document.getElementById(elementId)
      if (!el) return
      el.textContent = new Date().toLocaleTimeString('es-CO', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    }
    tick()
    setInterval(tick, 1000)
  }

  // ── Current Bimester ──
  window.getCurrentBimester = function () {
    var m = new Date().getMonth() + 1
    if (m <= 3) return 1
    if (m <= 6) return 2
    if (m <= 9) return 3
    return 4
  }

  // ── Escape HTML (XSS prevention) ──
  window.escapeHtml = function (text) {
    var div = document.createElement('div')
    div.appendChild(document.createTextNode(String(text || '')))
    return div.innerHTML
  }

  // ── Format Number ──
  window.formatNum = function (n, decimals) {
    var num = parseFloat(n)
    return isNaN(num) ? '--' : num.toFixed(decimals || 1)
  }

  console.log('[VYNTRA] Dashboard library loaded')
})()
