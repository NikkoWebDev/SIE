// VYNTRA Academic — Session Manager v3.1
// Auth via httpOnly cookie (JWT not accessible to JS)
(function () {
  var API_URL = window.__API_URL__ || 'http://localhost:8000'
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && !window.__API_URL__) {
    console.warn('[VYNTRA] window.__API_URL__ no definido. Usando fallback local. Setear PUBLIC_API_URL en el build.')
  }

  var origFetch
  var origOpen

  // ── Token is httpOnly — browser sends it automatically with credentials: 'include' ──
  function getToken() {
    return null // httpOnly cookie — not readable from JS
  }

  function isAuthenticated() {
    try {
      return !!localStorage.getItem('userId')
    } catch(e) { return false }
  }

  // ── Wake-up: ping server on every page load ──
  function wakeUp() {
    fetch(API_URL + '/api/health', { method: 'GET', priority: 'low', signal: AbortSignal.timeout(5000) }).catch(function(){})
  }

  // ── Auth check ──
  function checkAuth() {
    try {
      var userId = localStorage.getItem('userId')
      var publicPages = ['/', '/login', '/login/', '/api/health']

      if (!userId) {
        var path = window.location.pathname
        var isPublic = publicPages.some(function (p) { return path === p || path.startsWith('/api/') })
        if (!isPublic) {
          localStorage.clear()
          window.location.href = '/login/'
        }
        return false
      }
      return true
    } catch(e) { return false }
  }

  // ── Auto-logout on 401 responses ──
  function setupAuthInterceptor() {
    origOpen = XMLHttpRequest.prototype.open
    XMLHttpRequest.prototype.open = function () {
      this.addEventListener('load', function () {
        if (this.status === 401) {
          localStorage.clear()
          if (window.location.pathname !== '/login' && window.location.pathname !== '/login/') {
            window.location.href = '/login/'
          }
        }
      })
      return origOpen.apply(this, arguments)
    }

    origFetch = window.fetch
    window.fetch = function (url, opts) {
      return origFetch(url, opts).then(function (r) {
        if (r.status === 401) {
          localStorage.clear()
          if (window.location.pathname !== '/login' && window.location.pathname !== '/login/') {
            window.location.href = '/login/'
          }
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
  window.VYNTRA.isAuthenticated = isAuthenticated
  window.VYNTRA.getApiUrl = function () { return API_URL }
  window.VYNTRA.getToken = getToken
  window.VYNTRA.origFetch = origFetch
})()
