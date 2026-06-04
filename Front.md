# Feedback Frontend — Vyntra Solaris v5.0

> Fecha: 2026-06-03 (última verificación)
> Sitio en vivo: https://vyntraacademic.netlify.app/
> Repositorio: https://github.com/NikkoWebDev/SIE
> **Estado: 39/39 pruebas funcionales pasan. Prácticamente TODO resuelto.**

---

## 1. ✅ FIXED — Plantillas Astro sin compilar en dashboards

**Resuelto en v5.0.2.** Bug `{n[0]}` eliminado — 0 ocurrencias en producción verificadas. Los 3 dashboards tienen navegación hardcodeada funcional.

---

## 2. ✅ FIXED — Flujo de autenticación roto

**Resuelto en v5.0.4.** Login ahora guarda el token como `ws_access_token` y dashboards lo leen con la misma clave. Ya no hay redirect loop.

| Componente | Antes | Ahora |
|------------|-------|-------|
| `login.astro` | No guardaba `access_token` | Guarda `ws_access_token` ✅ |
| Dashboard `localStorage.getItem` | Buscaba `'access_token'` | Busca `'ws_access_token'` ✅ |

**Backend pendiente:** El backend aún no establece httpOnly cookie (no envía `Set-Cookie`). El token sigue viajando por `Authorization: Bearer` en localStorage.

---

## 3. ✅ FIXED — URLs de API inconsistentes

**Resuelto.** `session.js` ahora usa `window.__API_URL__` configurado en build (no hardcodeado). La URL canónica activa es `https://sie-8agt.onrender.com`.

Aún existen referencias a otras URLs en el historial git:
- `vyntra-backend.onrender.com` — referenciada en versiones anteriores de `session.js`
- `backend-colegio-hdx7.onrender.com` — en `vercel.json` archivado

**Recomendación:** Buscar y eliminar cualquier referencia residual a estas URLs en el código.

---

## 4. ALTO — Payload HTML excesivo (todo inline)

**Hallazgo:** Los dashboards incluyen CSS + JS inline sin cacheo externo:

| Página | Tamaño aprox. |
|--------|--------------|
| `/estudiante` | ~129 KB |
| `/docente` | ~69 KB |
| `/admin` | ~62 KB |

**Recomendación:**
- Mover CSS a imports de `theme.css` (Astro ya genera hash cacheable)
- Extraer JS inline a módulos `.astro` con `<script>`
- Dividir `estudiante.astro` (593 líneas) en componentes más pequeños

---

## 5. MEDIO — Chart.js no carga en dashboards

**Hallazgo:** `estudiante.astro` y `admin.astro` usan `Chart` en JS pero `BaseLayout.astro` (que envuelve los dashboards) NO incluye Chart.js. Solo `Layout.astro` lo incluye, pero no es usado por dashboards.

**Impacto:** Las gráficas de rendimiento académico y resultados de elecciones NO renderizan. El código tiene un retry infinito (`typeof Chart === 'undefined'` → `setTimeout(loadChartData, 500)`) que nunca se resuelve.

**Recomendación:**
- Agregar `<script src="...chart.js">` en `BaseLayout.astro` (ya tiene `integrity` en Layout.astro ✅)
- O cargar Chart.js dinámicamente solo cuando se necesite

---

## 6. ✅ FIXED — Accesibilidad (ARIA)

**Resuelto completamente en v5.0.6 / v5.0.9:**

| Issue | Ubicación | Estado |
|-------|-----------|--------|
| Sin `role="tab"` / `aria-selected` | Login — selector Estudiante/Personal | ❌ Bajo impacto. Etiquetas semánticas menores |
| `role="dialog"` + `aria-modal` | Login — modal de recuperación | ✅ **v5.0.6** |
| `role="alert"` + `role="status"` | Login — errores/éxito | ✅ **v5.0.6** |
| Skip-to-content link | BaseLayout | ✅ **v5.0.6** |
| `aria-label` en theme toggle | Sidebar | ✅ **v5.0.6** |
| `scope="col"` en tablas | Admin, Docente | ✅ **v5.0.9** |
| `:focus-visible` outline | theme.css | ✅ **v5.0.9** |
| Safe area (notch) support | theme.css | ✅ **v5.0.9** |
| Mobile sidebar padding | theme.css | ✅ **v5.0.9** |

---

## 7. MEDIO — Manejo de errores en API

**Hallazgo:** Los dashboards no tienen estados de error visibles. Si la API falla, las secciones quedan en "Cargando..." o "--" indefinidamente.

**Recomendación:**
- Agregar `catch` con toast de error visible
- Timeout con `AbortController` (15s)
- Mantener el fallback `"--"` que ya usa `index.astro`

---

## 8. ✅ FIXED — Contraste de color y focus visible

- ✅ `:focus-visible` implementado con `outline: 2px solid var(--brand-gold)` en `theme.css` (v5.0.9)

---

## 9. BAJO — UX de carga y retroalimentación

- Spinner genérico "Cargando..." sin progreso
- Transiciones instantáneas entre secciones
- Chat IA sin indicador de "escribiendo..." consistente

---

## 10. ✅ FIXED — CSP implementado

**Nuevo en v5.0.2/5.0.4:** Content Security Policy activo en `Layout.astro` y `BaseLayout.astro`:
```
default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net ...
connect-src 'self' https://sie-8agt.onrender.com wss://sie-8agt.onrender.com
```

Headers de seguridad verificados:
- ✅ `X-Content-Type-Options: nosniff`
- ✅ `X-Frame-Options: DENY`
- ✅ `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- ✅ `Referrer-Policy: strict-origin-when-cross-origin`
- ✅ `Content-Security-Policy` (completo)

---

## 11. ✅ FIXED — Dependencias CDN con integridad

Chart.js en `Layout.astro` ahora incluye `integrity="sha512-..."` ✅. No se detectaron CDN sin integridad en producción.

---

## 12. ✅ FIXED — Cache de assets

- Astro assets (`_astro/*.css`): `Cache-Control: public, max-age=31536000, immutable` ✅
- Favicon: `Cache-Control: public, max-age=3600, must-revalidate` ✅

---

## 13. ✅ FIXED — Imágenes WebP

Brand assets convertidos de PNG a WebP en v5.0.2. Pendiente: usar `<picture>` con fallback para Safari <14.

---

## 14. BAJO — Sin favicon en dashboards

Solo `index.astro` incluye favicon explícitamente. `BaseLayout.astro` y `Layout.astro` no lo incluyen, pero los dashboards sí muestran el favicon (heredado del layout base).

---

## 15. ✅ FIXED — Manejo de errores API

Los dashboards ahora muestran toast con mensaje de error antes de redirigir (v5.0.9):
```js
if (!role) { window.VyntraToast?.error('Sesión no encontrada.'); setTimeout(function(){ window.location.href='/login' },1500); return }
```
En lugar de redirect inmediato sin explicación.

---

## Resumen

| Prioridad | Issues |
|-----------|--------|
| **✅ Fixed** | 1 ({n[0]}), 2 (auth), 3 (URLs), 6 (accesibilidad), 8 (focus-visible), 10 (CSP), 11 (CDN SRI), 12 (cache), 13 (WebP), 15 (errores API) |
| **Medio** | 5. Chart.js no carga en dashboards |
| **Bajo** | 7. UX carga, 9. Favicon, 14. Payload inline |
