// VYNTRA Academic — Session Manager v1.0
// Shared auth verification + server wake-up
(function () {
  var API_URL = (window.__API_URL__ || document.querySelector('meta[name="api-url"]')?.getAttribute('content')) || 'https://vyntra-backend.onrender.com'
  // Fallback to localhost if running locally
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    API_URL = 'http://localhost:8000'
  }

  // ── Wake-up: ping server on every page load ──
  function wakeUp() {
    var xhr = new XMLHttpRequest()
    xhr.open('GET', API_URL + '/api/health', true)
    xhr.setRequestHeader('Cache-Control', 'no-cache')
    xhr.timeout = 10000
    xhr.send()
  }

  // ── Auth check ──
  function checkAuth() {
    try {
      var token = localStorage.getItem('access_token')
      var userId = localStorage.getItem('userId')
      var publicPages = ['/', '/login', '/api/health']

      if (!token || !userId) {
        var path = window.location.pathname
        var isPublic = publicPages.some(function (p) { return path === p || path.startsWith('/api/') })
        if (!isPublic) {
          localStorage.clear()
          window.location.href = '/login'
        }
        return null
      }
      return token
    } catch(e) { return null }
  }

  // ── Parse JWT payload ──
  function parseToken(token) {
    try {
      var parts = token.split('.')
      if (parts.length !== 3) return null
      return JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
    } catch (e) {
      return null
    }
  }

  // ── Check if token is expired ──
  function isTokenExpired(token) {
    var payload = parseToken(token)
    if (!payload || !payload.exp) return true
    return Date.now() >= payload.exp * 1000
  }

  // ── Auto-logout on 401 responses ──
  function setupAuthInterceptor() {
    var origOpen = XMLHttpRequest.prototype.open
    XMLHttpRequest.prototype.open = function () {
      this.addEventListener('load', function () {
        if (this.status === 401) {
          localStorage.clear()
          window.location.href = '/login'
        }
      })
      return origOpen.apply(this, arguments)
    }

    // Also intercept fetch
    var origFetch = window.fetch
    window.fetch = function (url, opts) {
      return origFetch(url, opts).then(function (r) {
        if (r.status === 401) {
          localStorage.clear()
          window.location.href = '/login'
        }
        return r
      })
    }
  }

  // ── Init ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      checkAuth()
      wakeUp()
      setupAuthInterceptor()
    })
  } else {
    checkAuth()
    wakeUp()
    setupAuthInterceptor()
  }

  // Expose helpers globally
  window.VYNTRA = window.VYNTRA || {}
  window.VYNTRA.parseToken = parseToken
  window.VYNTRA.isTokenExpired = isTokenExpired
  window.VYNTRA.getApiUrl = function () { return API_URL }
})()
