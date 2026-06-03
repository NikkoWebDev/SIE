// VYNTRA Academic — Session Manager v2.0
// Security: Supports both httpOnly cookie and localStorage JWT
(function () {
  var API_URL = (window.__API_URL__ || document.querySelector('meta[name="api-url"]')?.getAttribute('content')) || 'https://vyntra-backend.onrender.com'
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    API_URL = 'http://localhost:8000'
  }

  // ── Get token from cookie or localStorage ──
  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
    return match ? decodeURIComponent(match[2]) : null
  }

  function getToken() {
    // Prefer httpOnly cookie (set by backend, more secure)
    var cookieToken = getCookie('access_token')
    if (cookieToken) return cookieToken
    // Fallback to localStorage for backward compatibility
    try {
      return localStorage.getItem('access_token')
    } catch(e) { return null }
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
      var token = getToken()
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

  // ── Parse JWT payload (client-side, no signature verification) ──
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
  window.VYNTRA.getToken = getToken
})()
