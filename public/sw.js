var CACHE = 'vyntra-v1'
var SHELL = [
  '/',
  '/login',
  '/favicon.svg',
  '/manifest.webmanifest'
]

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL)
    }).then(function () {
      return self.skipWaiting()
    })
  )
})

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE }).map(function (k) { return caches.delete(k) })
      )
    }).then(function () {
      return self.clients.claim()
    })
  )
})

self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url)

  // Only handle same-origin GET requests
  if (e.request.method !== 'GET' || url.origin !== location.origin) return

  // Don't cache API calls or WebSocket
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) return

  // Network-first for HTML (always get fresh content)
  if (url.pathname === '/' || url.pathname.endsWith('.html') || !url.pathname.includes('.')) {
    e.respondWith(
      fetch(e.request).catch(function () {
        return caches.match(e.request)
      })
    )
    return
  }

  // Cache-first for static assets
  e.respondWith(
    caches.match(e.request).then(function (hit) {
      return hit || fetch(e.request).then(function (res) {
        var clone = res.clone()
        caches.open(CACHE).then(function (cache) { cache.put(e.request, clone) })
        return res
      })
    })
  )
})
