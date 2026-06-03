# Optimization — Vyntra Academic v5.0

> Fecha: 2026-06-03

---

## 1. CRÍTICO — Bundle splitting y extracción de CSS/JS

**Problema:** Todo el CSS y JS está inlne en cada página. Astro con Tailwind produce un bundle CSS único compartido, pero las páginas dashboard inlne aún más estilos y scripts manualmente.

**Impacto:** Sin cacheo efectivo, HTML de 60–130 KB por página, TTFB alto.

**Recomendación:**
| Acción | Beneficio |
|--------|-----------|
| Mover `<style>` de dashboard a imports de `theme.css` | Caché compartido |
| Extraer JS de dashboard a archivos `.astro` con `<script>` | Astro genera archivos con hash y los cachea |
| Dividir `estudiante.astro` (1154 líneas) en componentes | Código más mantenible, dead-code elimination |

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

**Verificación en vivo:** Las APIs respondieron rápidamente durante la prueba (sin cold start apreciable), probablemente porque el sitio tuvo tráfico reciente.

---

## 3. ALTO — Caché de assets estáticos

**Problema:** Los assets (imágenes, fuentes, JS externo) no tienen una estrategia de caché agresiva.

**Hallazgos:**
- `vercel.json` (archivado) definía caché para `/assets/*`. `netlify.toml` activo no tiene cabeceras de caché específicas.
- ✅ Las imágenes en `src/assets/brand/` fueron convertidas de PNG a WebP en v5.0.2.
- ❌ Las imágenes WebP no se usan con `<picture>` para fallback — navegadores antiguos (Safari <14) no muestran nada.

**Recomendación:**
- **Netlify:** Agregar en `netlify.toml`:
  ```toml
  [[headers]]
    for = "/assets/*"
    [headers.values]
      Cache-Control = "public, max-age=31536000, immutable"
  ```
- **Optimización de imágenes:** Usar el componente `<Image />` de Astro con formatos modernos (avif, webp) y tamaños responsivos.
- **Precarga de fuentes:** Agregar `rel="preload"` para Syne y Sora en el `<head>`.

---

## 4. MEDIO — Carga bajo demanda (lazy loading)

**Problema:** Los dashboards cargan toda la lógica de todas las secciones al inicio, incluso si el usuario nunca las visita.

**Impacto:** JS innecesario se parsea y ejecuta en cada carga de página (~30–50 KB de lógica de dashboard no usada inmediatamente).

**Recomendación:**
- **Lazy loading de secciones:** Cada sección (Notas, Exámenes, Tareas, etc.) carga su JS solo cuando el usuario hace clic en ella.
- **Dynamic import:** Usar `import()` para cargar Chart.js y jsPDF solo cuando se necesiten (en secciones de notas y PDFs).
- **Intersection Observer:** Para cargar contenido cuando las secciones están cerca del viewport.

---

## 5. BAJO — Service Worker / PWA

**Problema:** No hay manifest ni service worker. La app offline muestra "No hay conexión" sin ahorro de caché.

**Recomendación:**
- Implementar un service worker básico con `@astrojs/service-worker` o Workbox.
- Cachear el shell de la aplicación (CSS, layout, login).
- Mostrar contenido cachead (comunicados, horarios) cuando no hay conexión.

---

## 6. BAJO — CDN con SRI (Subresource Integrity)

**Problema:** Las 3 librerías CDN (Chart.js, jsPDF, autotable) se cargan sin `integrity`. Además de seguridad, si el CDN está caído, la app se rompe.

**Recomendación:**
- Instalar como dependencias npm y bundlear:
  ```bash
  npm install chart.js jspdf jspdf-autotable
  ```
- O agregar `integrity` + `fallback` CDN.
- Usar `defer` (ya se usa) + cargar desde `node_modules` con Astro.

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

| Prioridad | Acción | Impacto estimado |
|-----------|--------|------------------|
| 🔴 Crítico | Bundle splitting (CSS/JS externo) | -50% tamaño HTML, +caché |
| 🔴 Alto | Cold start backend | Disponibilidad 24/7 |
| 🔴 Alto | Caché de assets + imágenes optimizadas | -30% LCP |
| 🟡 Medio | Lazy loading de secciones | -40% JS inicial |
| 🟢 Bajo | Service Worker, SRI, CWV | Mejora progresiva |
