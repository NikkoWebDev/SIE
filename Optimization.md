# Optimization — Vyntra Solaris v5.0

> Fecha: 2026-06-03 (última verificación)
> **Estado: Casi todo resuelto. 2 items pendientes (bajo impacto).**

---

## 1. BAJO — Bundle splitting (mejora continua)

**Estado:** Astro assets cacheados 1 año ✅. El JS/CSS inline en dashboards NO es crítico — el HTML se comprime con Brotli en Netlify. Mejora opcional.

---

## 2. ALTO — Cold start del backend en Render

**Problema:** El backend FastAPI está en `render.com` (plan gratuito). Sin tráfico por ~15 minutos, Render suspende el servicio. El próximo request tarda 30–60 segundos (cold start).

**Impacto:** Primer login de la mañana, o después de períodos de inactividad, es IMPOSIBLE hasta que el backend despierte. Las tarjetas de estadísticas y comunicados en la página principal también fallan.

**Recomendación:**
- **Cron job de keep-alive:** Usar un servicio como cron-job.org o UptimeRobot para hacer ping a `https://sie-8agt.onrender.com/api/health` cada 10 minutos.
- **Startup script:** Optimizar `Dockerfile` para cold start más rápido (más capas cacheadas).
- **Plan de pago:** Render paga ($7/mes) elimina el cold start.
- **Backend warmup endpoint:** Crear un endpoint que precargue cachés y conexiones a Supabase.

**Estado actual:** El script `session.js` ya hace un ping a `/api/health` en cada carga de página. La URL del backend ahora se pasa via `window.__API_URL__` desde el build (ya no hardcodeada). Sin embargo, el keep-alive sigue sin ser suficiente para mantener el backend activo durante la noche.

**Verificación en vivo:** APIs respondieron en <2s durante la prueba (34 tests, 3 roles). Sin cold start apreciable.

**Recomendación adicional:** Existe `scripts/keep-alive.sh` en el repo — implementar como cron job externo (cron-job.org) para mantener el backend activo 24/7.

---

## 3. ALTO — Caché de assets estáticos

**Problema:** Los assets (imágenes, fuentes, JS externo) no tienen una estrategia de caché agresiva.

**Hallazgos:**
- `vercel.json` (archivado) definía caché para `/assets/*`. `netlify.toml` activo no tiene cabeceras de caché específicas.
- ✅ Las imágenes en `src/assets/brand/` fueron convertidas de PNG a WebP en v5.0.2.
- ❌ Las imágenes WebP no se usan con `<picture>` para fallback — navegadores antiguos (Safari <14) no muestran nada.

**Recomendación:**
- **Netlify:** Ya tiene caché para `_astro/*` (Astro lo maneja). Verificado: `max-age=31536000, immutable` ✅
- **Imágenes WebP:** Convertidas en v5.0.2. Pendiente: `<picture>` con fallback PNG para Safari <14
- **Precarga de fuentes:** Agregar `rel="preload"` para Syne y Sora en el `<head>`

---

## 4. MEDIO — Carga bajo demanda (lazy loading)

**Problema:** Los dashboards cargan toda la lógica de todas las secciones al inicio.

**Impacto:** JS innecesario se parsea en cada carga (~30–50 KB no usado inmediatamente).

**Recomendación:**
- **Dynamic import:** Cargar Chart.js y jsPDF solo cuando se necesiten
- Las secciones ya se muestran/ocultan con `display:none`/`block` — siguiente paso: lazy load de datos y librerías

---

## 5. BAJO — Service Worker / PWA

**Problema:** No hay manifest ni service worker. La app offline muestra "No hay conexión" sin ahorro de caché.

**Recomendación:**
- Implementar un service worker básico con `@astrojs/service-worker` o Workbox.
- Cachear el shell de la aplicación (CSS, layout, login).
- Mostrar contenido cachead (comunicados, horarios) cuando no hay conexión.

---

## 6. ✅ FIXED — CDN con SRI (Subresource Integrity)

**Resuelto.** Chart.js en `Layout.astro` incluye `integrity` SHA-384. Layout.astro no es usado por dashboards (usan BaseLayout), pero la librería está protegida donde se carga.

**Pendiente:** jsPDF y autotable no se cargan desde CDN actualmente — se cargarían dinámicamente si se implementa el export PDF.

---

## 7. BAJO — Métricas Core Web Vitals

**Problemas detectados:**

| Métrica | Estado | Recomendación |
|---------|--------|---------------|
| LCP | Potencialmente alto (inline CSS + font load) | Preload de fuentes, CSS crítico inline solo para el pliegue |
| FID/INP | Aceptable (sin JS pesado en carga inicial) | Mantener, monitorear con Sentry |
| CLS | Bueno (layout mayormente estático) | Verificar que skeletons tengan altura definida |
| TTFB | Lento por cold start de Render | Keep-alive + backend warmup |

---

## 8. BAJO — Compresión y minificación

**Problema:** Verificar que Netlify/Vercel apliquen compresión Brotli/Gzip a los HTML grandes de dashboard.

**Recomendación:**
- Netlify comprime automáticamente. Verificar en los headers de respuesta.
- El build de Astro ya minifica HTML, CSS y JS. Confirmar que no hay config desactivando minificación.

---

## Resumen de prioridades

| Prioridad | Acción | Estado |
|-----------|--------|--------|
| 🔴 Alto | Cold start backend | ⚠️ Keep-alive script existe, falta cron externo |
| 🟢 Bajo | Bundle splitting | Mejora continua, no crítico |
| 🟢 Bajo | Lazy loading secciones | Mejora continua |
| 🟢 Bajo | Chart.js en dashboards | Bajo impacto (no usado actualmente) |
| 🟢 Bajo | Service Worker / PWA | Mejora futura |
| ✅ Fixed | Caché de assets (1 año immutable) | Verificado |
| ✅ Fixed | Imágenes WebP | v5.0.2 |
| ✅ Fixed | SRI en Chart.js | Verificado |
