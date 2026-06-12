# VYNTRA Academic — Frontend Completo

**Última actualización:** 2026-06-07 (post-refinement v2)
**Framework:** Astro v5 (output: static, adapter: Netlify)
**UI:** Tailwind CSS v3 + CSS custom properties + motion system (theme.css)
**Animaciones:** GSAP + ScrollTrigger (landing, CTA persistente, progress bar, matchMedia mobile)
**Gráficos:** Chart.js v4 (carga lazy vía dynamic import, no en bundle inicial)
**IA:** OpenRouter API streaming chat vía backend (AbortController + botón Detener + section context + placeholder dinámico)
**Auth:** JWT HS256 — httpOnly cookie + `ws_access_token` localStorage auxiliar. CSRF Double Submit Cookie.
**Type check:** 0 errors, 0 warnings
**Backend URL:** `https://sie-8agt.onrender.com`

---

## Arquitectura de Componentes

```
BaseLayout.astro ← RAÍZ: CSP, SEO, theme, session, vfetch, auth interceptor
                   Scripts en 4 fases (inline sync + module async).
                   Importa via <script>: api.ts, session.ts, section-router.ts, charts.ts
  ├── Páginas públicas (index, login, 404)
  └── DashboardShell.astro ← Sidebar + Topbar + Toast + LoadingOverlay
                              (Chart.js YA NO se carga aquí — es lazy)
        ├── Sidebar.astro + Topbar.astro
        ├── Dashboards (estudiante, docente, admin)
        ├── AIChat.astro (flotante, AbortController + Stop + section context + placeholder dinámico)
        └── WsRiskAlert.astro (solo estudiante, cleanup en beforeunload)
```

---

## Árbol de archivos (31 archivos)

```
src/
├── lib/
│   ├── api.ts              ★ Fetch unificado: vfetch, apiFetch, postJson, postForm
│   ├── session.ts          ★ Sesión unificada: logout, storeSession, getRole, requireAuth
│   ├── section-router.ts   ★ Navegación por secciones con lazy loaders
│   ├── charts.ts           ★ Chart.js dinámico: getChartJS, getChartWhenReady
│   └── types.ts            Tipos TypeScript + declaraciones globales Window
├── layouts/
│   └── BaseLayout.astro    ★ Raíz: CSP, SEO, fonts, theme, vfetch, auth interceptor
├── components/
│   ├── layout/
│   │   ├── DashboardShell.astro  ★ Chart.js static import ELIMINADO
│   │   ├── Sidebar.astro         ★ Logout unificado vía VyntraSession, aria-current, active gradient transition
│   │   └── Topbar.astro          ★ Escape cierra menú móvil
│   ├── ui/
│   │   ├── Toast.astro           Sin cambios estructurales
│   │   └── LoadingOverlay.astro  Sin cambios
│   ├── AIChat.astro              ★ AbortController + Stop + section context indicator + placeholder dinámico + msg fade-in
│   ├── WsRiskAlert.astro         ★ Cleanup beforeunload, audio requiere gesture
│   ├── Logo.astro                Sin cambios
│   └── SEOHead.astro             Sin cambios
├── pages/
│   ├── index.astro               ★ ScrollTrigger cleanup + progress bar + floating CTA + matchMedia mobile
│   ├── login.astro               ★ Validación inline, sin no-cors, sesión unificada
│   ├── dashboard.astro           ★ Redirect vía VyntraSession
│   ├── estudiante.astro          ★ +.jpeg, Chart lazy, catches con feedback, solar-card, card-stagger
│   ├── docente.astro             ★ Catches con console.error, solar-card, card-stagger
│   ├── admin.astro               ★ Chart lazy, sin setTimeout race, solar-card, card-stagger
│   ├── 404.astro                 Sin cambios
│   └── api/assets.ts             Sin cambios
├── styles/
│   └── theme.css                 CSS vars + motion system + card system + microinteractions + progress/floating CTA
└── assets/brand/                 Logos VYNTRA (7 imágenes)
```

---

## Módulos (src/lib/)

### `api.ts` — Fetch Unificado

```ts
createTimeoutSignal(ms = 15000) → { signal, clear }
apiFetch(path, opts?) → Promise<any>      // auto-prepends API_URL, maneja 401, parsea JSON
vfetch(baseUrl, path, opts?) → Promise<Response>  // compatibilidad backwards con páginas legacy
postJson(path, body, opts?) → Promise<any>
postForm(path, formData, opts?) → Promise<any>
```

**Expone en window:** `apiFetch`, `vfetch`, `createTimeoutSignal`
**Timeout:** `AbortController` manual (sin `AbortSignal.timeout`)
**401:** limpia localStorage, toast, redirect a `/login`

### `session.ts` — Sesión Unificada

```ts
getUser() → { userId, userRole, userName, profile_id, userGrade } | null
getRole() → 'student' | 'teacher' | 'admin' | null
isAuthenticated() → boolean
clearSession() → void
logout() → Promise<void>       // POST /api/auth/logout + clear + redirect /
redirectToRole(role?) → void
requireAuth() → boolean
storeSession(data) → void      // guarda ws_access_token + metadata en localStorage
```

**Expone en window:** `VyntraSession = { getUser, getRole, isAuthenticated, clearSession, logout, redirectToRole, requireAuth, storeSession }`
**Principio:** httpOnly cookie = auth real. localStorage = UX metadata.

### `section-router.ts` — Navegación por Secciones

```ts
createSectionRouter({
  titles, subtitles,          // mapas de texto para topbar
  loaders,                    // { sectionId: () => void } — lazy, ejecutados 1 vez
  onNavigate?, startSection?,
  defaultSection?, titleSelector?, subtitleSelector?
}) → { showSection(id?, force?), reloadSection(id), getCurrentSection() }
```

**Expone en window:** `createSectionRouter`
**Características:** lazy load, force reload, `vyntra:navigate` CustomEvent, errores con toast automático.

### `charts.ts` — Chart.js Dinámico

```ts
getChartJS() → Promise<{ Chart, registerables }>    // import('chart.js') dinámico
getChartWhenReady() → Promise<Chart>                // resuelve cuando está disponible
destroyChart(canvas) → void
```

**Expone en window:** `getChartJS`, `getChartWhenReady`
**Emite:** evento `chart:ready` (CustomEvent) cuando Chart.js carga
**Setea:** `window.Chart` al cargar por primera vez
**Bundle:** ~206 KB como chunk separado, NO en bundle inicial de ningún dashboard

---

## BaseLayout.astro — Scripts (4 fases)

```
Fase 1 (is:inline, sync):  window.__API_URL__ + theme init (FOUC prevention)
Fase 2 (is:inline, early): Auth check + wakeUp (XMLHttpRequest) + XHR 401 interceptor
Fase 3 (is:inline, early): Utilidades puras (escapeHtml, formatNum, vfetch, startVyntraClock, getCurrentBimester)
Fase 4 (<script> module):  import api.ts + session.ts + section-router.ts + charts.ts
```

---

## API Surface Global (`window`)

### Funciones Core (BaseLayout.astro, Fase 3)

| Propiedad | Descripción |
|-----------|-------------|
| `__API_URL__` | URL del backend |
| `setVyntraTheme(dark)` | Toggle tema claro/oscuro |
| `vfetch(baseUrl, path, opts)` | Fetch con timeout 15s, 401 handling |
| `escapeHtml(text)` | Sanitización XSS via createTextNode |
| `formatNum(n, d)` | Formateo numérico con decimales |
| `startVyntraClock(elId)` | Reloj digital en vivo |
| `getCurrentBimester()` | Período académico actual (P1-P4) |

### Funciones de Módulos (BaseLayout.astro, Fase 4)

| Propiedad | Módulo | Descripción |
|-----------|--------|-------------|
| `apiFetch(path, opts)` | api.ts | Fetch con auto-prepend API_URL, parse JSON |
| `createTimeoutSignal(ms)` | api.ts | Factory AbortController + timer |
| `VyntraSession` | session.ts | `{ getUser, getRole, logout, storeSession, ... }` |
| `createSectionRouter(cfg)` | section-router.ts | Navegación con lazy loaders |
| `getChartJS()` | charts.ts | `import('chart.js')` dinámico |
| `getChartWhenReady()` | charts.ts | Promise que resuelve Chart cuando disponible |

### Componentes

| Propiedad | Origen | Descripción |
|-----------|--------|-------------|
| `VyntraToast` | Toast.astro | `{ show, success, error, warning, info }` |
| `VYNTRA` | BaseLayout.astro | `{ isAuthenticated, getApiUrl, getToken }` |
| `Chart` | charts.ts (al cargar) | Chart.js global (solo después de `getChartJS()`) |

---

## Motion System (theme.css)

### Design Tokens

```css
:root {
  --ease-out: cubic-bezier(0.19,1,0.22,1);
  --ease-inout: cubic-bezier(0.87,0,0.13,1);
  --ease-spring: cubic-bezier(0.34,1.56,0.64,1);
  --ease-smooth: cubic-bezier(0.33,1,0.68,1);     /* transiciones suaves */
  --ease-snap: cubic-bezier(0.4,0,0.2,1);          /* interacciones rápidas */
  --t-fast: 160ms;
  --t-base: 320ms;
  --t-slow: 640ms;
  --t-cinematic: 1200ms;
  --progress: 0;  /* scroll progress bar */
}
```

### .section-enter (dashboard navigation)

Navegación entre secciones usa `var(--t-base)` + `var(--ease-out)` con `scale(.98)` + `blur(6px)` → `none`.

### Card System

| Clase | Descripción |
|-------|-------------|
| `.solar-card` | Glassmorphism: fondo `rgba(255,255,255,0.75)` + blur(16px) + borde sutil. Dark mode incluido. |
| `.solar-card-hover` | Lift on hover: `translateY(-4px)` con box-shadow transición |
| `.solar-card-primary` | Borde gold + glow (`rgba(245,166,35,0.2)`) |
| `.solar-card-danger` | Borde rojo + glow (`rgba(220,38,38,0.2)`) |
| `.card-stagger` | Entrada staggered vía `@keyframes cardEnter` (opacity + translateY) |

Aplicado a todos los cards de dashboards (estudiante, docente, admin).

### Microinteractions

| Clase | Comportamiento |
|-------|----------------|
| `.solar-btn` | `hover: translateY(-1px)`, `active: scale(.98)` |
| `.solar-input:focus` | Gold ring (`3px rgba(245,166,35,.15)`) + shadow |
| `.solar-table tr:hover` | Highlight sutil en filas de tabla |
| `.msg-bubble` | Entrada de mensaje: `translateY(8px)` + fade-in; stagger automático en consecutivas |
| `.empty-state` | Contenedor centrado con ícono atenuado, texto, y acción sugerida |

---

## Páginas

### index.astro

- GSAP ScrollTrigger con 4 etapas (~410vh de scroll)
- `prefersReducedMotion` respetado: si activo, muestra todo estático
- **Progress bar:** `<div id="solar-progress">` fijo abajo, ancho animado via GSAP `--progress` + ScrollTrigger scrub
- **Floating CTA:** `<a id="floating-cta">` glassmorphism fijo bottom-right, aparece al scroll post-hero vía ScrollTrigger `toggleActions`
- **Mobile optimization:** `gsap.matchMedia()` reduce escala hero y ajusta posiciones en ≤768px
- **Cleanup:** `tl.kill()` + `mm.revert()` + `ScrollTrigger.getAll().forEach(st => st.kill())` en `beforeunload`
- 4 stat cards, 6 features, notices grid, CTA final

### login.astro

- **Validación inline:** blur + input en `#credential` y `#password`, errores en elementos con `aria-describedby`
- Health check sin `mode: 'no-cors'`
- Doble submit prevenido con flag `submitting`
- Sesión: usa `VyntraSession.storeSession()` si disponible, fallback manual
- Recuperación de contraseña con texto honesto: "Si no recibiste el código, contacta a secretaría."

### estudiante.astro

- `accept=".pdf,.doc,.docx,.zip,.png,.jpg,.jpeg"` (jpeg agregado)
- `loadChartData()`: usa `getChartWhenReady()` en vez de `setTimeout` polling
- 5 funciones con catches ahora muestran toast + `console.error`: `loadExams`, `loadSchedule`, `loadLibrary`, `loadCandidates`, `loadWelcomeData`
- Grade cache (`fetchGrades`) con caché in-memory — elimina llamadas duplicadas
- **Staggered cards:** `staggerCards(sec)` añade `card-stagger` con 0.04s delay por tarjeta al navegar entre 9 secciones
- **Clases aplicadas:** `solar-card` + `solar-card-hover` en stat cards y content cards

### docente.astro

- 6 catches ahora loguean `console.error('[docente] ...')` con mensajes de reintento
- `populateGradeSelects()`: grados 6-A → 11-B predefinidos
- `loadSubjectsForGrade()`: materias filtradas por grado vía API
- **Staggered cards:** `staggerCards(sec)` en navegación entre 7 secciones
- **Clases aplicadas:** `solar-card` + `solar-card-hover` en todos los cards

### admin.astro

- `renderElectionChart()`: usa `getChartWhenReady()` en vez de `setTimeout`
- `loadAllData()`: `Promise.allSettled` con cache, AbortController para cancelación
- **Staggered cards:** `staggerCards(sec)` en navegación entre 7 secciones
- **Clases aplicadas:** `solar-card` + `solar-card-hover` en stat cards, content cards, y modal

### dashboard.astro

- Redirect usa `VyntraSession.getRole()` y `VyntraSession.redirectToRole()` si disponibles
- Fallback al mapping `localStorage` → role map

---

## AIChat.astro

- **AbortController** (`currentAbortController`): cancela streaming SSE
- **Botón Detener** (`#chat-stop`): visible durante streaming, oculto al terminar
- **Payload con contexto:** escucha `vyntra:navigate`, envía `{ message, section }`
- **Section context indicator:** muestra "Estás en: Notas" en el header del chat, mapea 20+ section IDs a nombres legibles
- **Placeholder dinámico:** cambia según la sección activa (ej: "Pregunta sobre tus notas...", "¿Dudas con algún examen?")
- **Message fade-in:** todas las burbujas tienen `.msg-bubble` con animación de entrada + stagger automático
- **Errores:** toast de conexión, `AbortError` → "[Generación detenida]"
- localStorage persistence (max 50 mensajes), clear button
- SSE streaming con `res.body.getReader()`
- Sugerencias contextuales por rol (student/teacher/admin)
- Markdown básico: headers, bold, italic, code

---

## WsRiskAlert.astro

- WebSocket con JWT (`ws_access_token`), reconexión exponencial (1s → 30s)
- **Cleanup `beforeunload`:** `destroyed = true`, cierra WS, `clearTimeout(reconnectTimer)`, `audioCtx.close()`
- **Audio requiere user gesture:** `hasUserGesture` flag, no reproduce sin click/tecla previa
- **`storage` event:** detecta logout (borrado de `ws_access_token`)
- `AudioContext` reuse (una instancia)
- Toast visual con auto-dismiss 8s + botón cerrar

---

## Componentes Base

### DashboardShell.astro

- Chart.js static import ELIMINADO (~202 KB fuera del bundle inicial)
- Sidebar, Topbar, Toast, LoadingOverlay, noise overlay
- `aria-live="polite"` en todas las secciones `[id^="sec-"]`

### Sidebar.astro

- **Logout:** `VyntraSession.logout()` → POST `/api/auth/logout` + clear localStorage + redirect `/`
  - Fallback directo si `VyntraSession` no está disponible
- Navegación vía `addEventListener('click')` → despacha `vyntra:navigate` CustomEvent
- `aria-current="page"` en sección activa (actualizado por listener de `vyntra:navigate`)
- **Active state**: gradiente maroon/gold en borde izquierdo + box-shadow inset + transición suave
- Configs por rol: student (9 secciones), teacher (7), admin (7)
- Mobile: sidebar oculto con `-translate-x-full lg:!translate-x-0`

### Topbar.astro

- **Escape key** cierra menú móvil y retorna foco al botón hamburguesa
- Sticky con nav-blur (glassmorphism)
- Indicador "En línea" con ping animation
- Reloj digital solo para role `student`
- TypeScript: casts `HTMLElement` para narrowing types en callbacks

---

## Configuración

### astro.config.mjs

```js
export default defineConfig({
  output: 'static',
  adapter: netlify({}),
  integrations: [tailwind(), sitemap()],
  site: 'https://colegiociudaddelsol.edu.co',
  build: { inlineStylesheets: 'never' },
  vite: {
    build: {
      minify: 'terser',
      cssMinify: 'lightningcss',
      rollupOptions: {
        output: {
          manualChunks: {
            jspdf: ['jspdf', 'jspdf-autotable'],
          },
        },
      },
    },
  },
})
```

**Nota:** `chartjs` eliminado de `manualChunks` — Vite maneja el chunking con el dynamic import de `charts.ts`.

---

## Bugs Resueltos (acumulado)

| ID | Descripción | Estado |
|----|-------------|--------|
| E1-E3 | CSS vars faltantes en theme.css | ✅ Resuelto |
| E4 | Fetch interceptor duplicado en BaseLayout | ✅ Resuelto |
| E5 | XSS en index.astro noticias | ✅ Resuelto |
| E6 | Selects de grado/materia en docente | ✅ Resuelto |
| E7 | Grade data cache en estudiante | ✅ Resuelto |
| E8 | Falta `.jpeg` en accept de tareas | ✅ Resuelto |
| M1 | `onclick` + `addEventListener` mezclados | ✅ Sidebar/Topbar migrados |
| M2 | Catches silenciosos sin feedback | ✅ 0 en todo src/ |
| M3 | Race condition Chart.js con `setTimeout` | ✅ Reemplazado por `getChartWhenReady()` |
| M5 | Service Worker desactivado siempre | ✅ Documentado |
| M6 | Sin validación inline en formularios | ✅ Login con blur+input |
| M7 | `AbortSignal.timeout` sin polyfill | ✅ Reemplazado por `AbortController` manual |
| M8 | Health check `mode:'no-cors'` inútil | ✅ Eliminado |
| M10 | `style="display:none"` inline | ✅ Archivo legacy eliminado |
| S1 | Layout.astro legacy no usado | ✅ Eliminado |
| S2 | session.js código muerto | ✅ Eliminado |
| S3 | Tests E2E esperan tabs de login inexistentes | ✅ Reescritos |
| — | nav.js y theme.js no usados | ✅ Eliminados |
| — | auth.ts reemplazado por session.ts | ✅ Eliminado |
| — | chartjs manualChunks redundante | ✅ Eliminado |
| — | ScrollTrigger sin cleanup | ✅ Agregado |
| — | 20 type errors en astro check | ✅ Corregidos |
| R1 | Sin motion system unificado (easing/duration tokens) | ✅ Agregado en :root |
| R2 | Sin glassmorphism system reutilizable en cards | ✅ `.solar-card` + hover/primary/danger |
| R3 | Sin microinteracciones en botones/inputs | ✅ `.solar-btn`, `.solar-input:focus` |
| R4 | Landing sin progress bar ni indicador de scroll | ✅ `#solar-progress` con GSAP scrub |
| R5 | Landing sin optimización mobile | ✅ `gsap.matchMedia()` ≤768px |
| R6 | AI Chat sin indicador visual de sección actual | ✅ "Estás en: X" en header |
| R7 | Landing sin CTA persistente post-hero | ✅ `#floating-cta` glassmorphism con ScrollTrigger |
| R8 | Sin entrada staggered de cards en dashboards | ✅ `staggerCards()` con `@keyframes cardEnter` |
| R9 | Sin placeholder dinámico en AI Chat | ✅ Placeholder varía por sección activa |
| R10 | Sin animación de entrada en mensajes de chat | ✅ `.msg-bubble` + stagger consecutivo |
| R11 | Sidebar sin transición en estado activo | ✅ border/color/background/box-shadow con `--ease-smooth` |
| R12 | Sin easings complementarios (smooth/snap) | ✅ `--ease-smooth`, `--ease-snap` agregados |
| R13 | Sin CSS de empty state reutilizable | ✅ `.empty-state` con ícono + texto + acción |
| R14 | Sin hover de filas de tabla | ✅ `.solar-table tr:hover` |

---

## Bugs Pendientes

| ID | Descripción | Nota |
|----|-------------|------|
| M4 | Estado localStorage vs cookie inconsistente | Mitigado con `VyntraSession`, falta verify call |
| M9 | Sin lazy loading real de secciones HTML | `createSectionRouter` tiene infraestructura, falta migrar páginas |
| M20 | Chart.js chunk separado se descarga al hacer dynamic import | Comportamiento correcto, 206 KB bajo demanda |

---

## Comandos

```bash
npm run dev         # astro dev (localhost:4321)
npm run build       # astro build (7 páginas, dist/)
npm run preview     # astro preview
npm run check       # astro check (0 errors, 0 warnings)
npm run test        # playwright test --project=ci
```

---

## Build Stats

```
dist/_astro/BaseLayout.astro_...js  → 6.33 KB   (módulos api/session/charts/router)
dist/_astro/index.astro_...js       → 115.9 KB  (landing GSAP + progress bar + floating CTA + matchMedia)
dist/_astro/chart....js             → 206 KB    (Chart.js, lazy, fuera del bundle inicial)
```

- 31 archivos fuente, 7 páginas, 0 errores de build
- Chart.js NO en bundle inicial de ningún dashboard
- Legacy eliminado: 5 archivos (Layout.astro, session.js, nav.js, theme.js, auth.ts)
