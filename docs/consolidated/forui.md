# VYNTRA Solaris — Diseño UI

> ⚠️ **Documento de DISEÑO INTENCIONAL.** Documenta cómo DEBERÍA funcionar el sistema. Puede diferir del código real. Para la realidad actual, ver `C_sol/claude.md`. Correcciones conocidas detalladas abajo. Documento vivo.

---

## 1. Arquitectura de páginas

```
index.astro          → Landing pública (scrollytelling)
login.astro           → Login público
estudiante.astro      → Dashboard estudiante (9 secciones)
docente.astro         → Dashboard docente (7 secciones)
admin.astro           → Dashboard admin (7 secciones)
dashboard.astro       → Redirect según rol (lee localStorage.userRole)
404.astro             → Error solar eclipse
```

Todas las páginas usan `BaseLayout` como wrapper raíz. Los dashboards además usan `DashboardShell` + `Sidebar` + `Topbar`.

> ⚠️ `Layout.astro` existe pero **NO es usado por ninguna página actual**. `public/js/session.js` solo se carga allí, por lo tanto tampoco se ejecuta en producción.

---

## 2. BaseLayout — envolvente raíz de toda la app

**Archivo:** `src/layouts/BaseLayout.astro`

### Props

```astro
export interface Props {
  titulo: string            // <title> + OG
  descripcion?: string      // meta description
  noIndex?: boolean         // noindex para dashboards
  withNoise?: boolean       // overlay de ruido SVG fractal
}
```

### CSP (Content-Security-Policy)

Generado dinámicamente en el frontmatter:

```astro
const apiUrl = (import.meta.env.PUBLIC_API_URL || 'http://localhost:8000').replace(/\/+$/, '')
const apiHost = new URL(apiUrl).host
const wsScheme = apiUrl.startsWith('https') ? 'wss' : 'ws'
const connectSrc = `'self' ${apiUrl} ${wsScheme}://${apiHost}`
const CSP = `default-src 'self'; script-src ${scriptSrc}; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src ${connectSrc}; frame-src 'self' https:; media-src 'self' https:; object-src 'none'; base-uri 'self'; form-action 'self'`
Astro.response.headers.set('Content-Security-Policy', CSP)
```

### Scripts inline (orden de carga en <head>, todos `is:inline`)

| # | Script | Función |
|---|--------|---------|
| 1 | `window.__API_URL__` | Lee `<meta name="vyntra-api-url">` |
| 2 | Service Worker cleanup | Desregistra SW antiguos |
| 3 | **Session Manager v3.2** | `checkAuth()`, `wakeUp()`, 401 interceptor condicional |
| 4 | **Dashboard Utilities** | `setVyntraTheme`, `vfetch`, `vfetchJSON`, `escapeHtml`, `formatNum`, `getCurrentBimester`, `startVyntraClock` |

### Session Manager v3.2

```js
// checkAuth() - redirige a /login solo si NO hay userId Y no está en página pública
// setupAuthInterceptor() - intercepta fetch y XHR, solo redirect 401 si userId EXISTÍA
// wakeUp() - ping silencioso a /api/health para warm-up de Render

window.VYNTRA = window.VYNTRA || {}
window.VYNTRA.isAuthenticated = isAuthenticated
window.VYNTRA.getApiUrl = function () { return API_URL }
window.VYNTRA.getToken = getToken
window.VYNTRA.origFetch = origFetch
```

### Dashboard Utilities

```js
window.setVyntraTheme   = function(dark) { ... }  // toggle light/dark + persist
window.vfetch           = function(apiUrl, path, opts) { ... }  // fetch con cookie, 401 handler, timeout 15s
// ⚠️ NOTA: vfetchJSON NO existe en el código real. Usar vfetch() + .json() manualmente.
window.startVyntraClock = function(elId) { ... }  // reloj en vivo HH:MM:SS
window.getCurrentBimester = function() { ... }    // retorna 1-4 según mes
window.escapeHtml       = function(text) { ... }  // sanitización via createTextNode
window.formatNum        = function(n, d) { ... }  // formato numérico con decimales
```

### Tipografía (Google Fonts)

```
Fraunces  opsz 9..144  wght 500,700   → display (headings, logo)
DM Sans   opsz 9..40   wght 400,500,700 → body
```

---

## 3. Logo — SVG inline, sin fondo

**Archivo:** `src/components/Logo.astro`

### Props

```astro
export interface Props {
  size?: number       // default 64, escala width
  animated?: boolean  // añade clase animate-logo-breathe
  class?: string      // clases extra
}
```

### Estructura del SVG (256×206 viewBox)

```
1. Círculo glow exterior   → radialGradient #F5A623 0→30% opacity
2. 8 rayos corona          → alternando 75px y 68px, gradiente #F5A623→#FFD166→#C47F0A
3. Libro abajo             → rect maroon + 2 páginas crema + fold + bookmark dorado
4. Sol central             → círculo 76px diámetro + highlight + core blanco
5. Monograma "V"           → Fraunces 900, #6B1A1A, centrado en el núcleo
```

### Animación logo-breathe (CSS)

```css
@keyframes logo-breathe {
  0%, 100% { transform: scale(1); filter: drop-shadow(0 0 15px rgba(245,166,35,0.2)); }
  50% { transform: scale(1.06); filter: drop-shadow(0 0 35px rgba(245,166,35,0.4)); }
}
```

---

## 4. Landing — Page `/` 

**Archivo:** `src/pages/index.astro`

### Concepto: El Viaje del Sol

Un solo `<Logo>` viaja por la pantalla. El scroll controla su posición y el contenido que aparece a su alrededor. No hay logos duplicados.

### Estructura HTML

```html
<div id="journey">                    ← trigger de ScrollTrigger
  <div id="stage" class="sticky">     ← sticky top-0 h-screen
    <div id="sol">                    ← UN SOLO LOGO, absolute, viaja con GSAP
      <Logo size={170} />
      <svg>anillos orbitales</svg>
    </div>
    <div id="hero-text">...</div>     ← overlay hero, desaparece film-roll
    <div id="stats-cards">...</div>   ← 4 stats, opacity 0→1→0
    <div id="features-list">...</div> ← 6 features, opacity 0→1→0
    <div id="notices-grid">...</div>  ← comunicados API, opacity 0→1→0
    <div id="cta-final">...</div>     ← CTA final, opacity 0→1
  </div>
  <div style="height:110vh"></div>   ← spacer 1 (stats)
  <div style="height:110vh"></div>   ← spacer 2 (features)
  <div style="height:110vh"></div>   ← spacer 3 (notices)
  <div style="height:80vh"></div>    ← spacer 4 (CTA)
</div>
```

### GSAP Timeline (scrub 1.1, 0→1 en 410vh)

```js
const tl = gsap.timeline({
  scrollTrigger: { trigger: '#journey', start: 'top top', end: 'bottom bottom', scrub: 1.1 }
})

tl
  // 0-12%: hero text film-roll (rotationX: 90, blur, opacity 0)
  // 10-32%: sol desciende (y:80, x:-140), stats aparecen derecha → desaparecen
  // 32-58%: sol a izquierda (x:-260), features aparecen derecha → desaparecen
  // 58-80%: sol sube (y:-90, x:0), notices grid aparece → desaparece
  // 78-100%: sol al centro (x:0, y:0), CTA fade in
```

### Data loading (API)

```js
// fetchWithRetry: 3 intentos, usa window.VYNTRA.origFetch como fallback defensivo
// Stats: GET /api/admin/stats → pobla #stat-estudiantes, #stat-docentes, #stat-mora, #stat-avisos
// Notices: GET /api/notices → render cards en #notice-grid con categoría, título, extracto, fecha
```

### Tema

Modo claro exclusivo: fondo `var(--solar-cream)` (#FFFBF0), texto `var(--text)` (#2D1B0A).

---

## 5. Login — Page `/login`

**Archivo:** `src/pages/login.astro`

### Concepto: La Joya Central

Layout compacto centrado (360px max-width). El logo es la joya arriba del formulario. Sin selector de rol — el backend detecta por el formato del credential. Sin split panel, sin tabs de rol.

### Estructura

```html
<main class="min-h-screen flex items-center justify-center bg-[var(--solar-cream)]">
  <!-- Glow dorado detrás del logo -->
  <div class="fixed ... bg-brand-gold/[0.06] blur-[100px]"></div>

  <div class="max-w-[360px]">        ← columna única, NO estirada
    <Logo size={130} />              ← la joya, 130px, con drop-shadow dorado
    <h1>VYNTRA Solaris</h1>          ← Fraunces, "Solaris" en dorado
    <p>Portal Académico · v5.0</p>

    <form id="login-form">
      <input id="credential">        ← ID institucional (único campo de identificación)
      <input id="password">          ← contraseña
      <button>Ingresar al Portal</button>
    </form>

    <button id="forgot-link">¿Problemas?</button>
  </div>
</main>
```

### Flujo de login (JS inline)

```js
form.addEventListener('submit', async function(e) {
  // POST /api/auth/login { login_credential, password }
  // Backend responde con { access_token, usuario: { rol, nombre, profile_id } }
  //   + Set-Cookie: access_token (httpOnly) + csrf_token
  // localStorage: ws_access_token (solo WebSocket), userRole, userName, userId, profile_id, userGrade
  // Redirect: map[role] → /estudiante, /docente, /admin
})
```

### Recuperación de contraseña (modal 2 pasos)

```html
<div id="forgot-modal">           ← backdrop blur, bg blanco
  <div id="forgot-step-1">        ← input credential → POST /api/auth/forgot-password
    <input id="forgot-credential">
    <button>Enviar Código</button>
  </div>
  <div id="forgot-step-2">        ← código 6 dígitos + nueva pass → POST /api/auth/reset-password
    <input id="forgot-code">
    <input id="forgot-new-pass">
    <input id="forgot-confirm-pass">
    <button>Restablecer</button>
  </div>
</div>
```

---

## 6. Dashboard Shell — estructura compartida

**Archivo:** `src/components/layout/DashboardShell.astro`

### Props

```astro
export interface Props {
  role: 'student' | 'teacher' | 'admin'
  activeSection?: string    // default 'inicio'
  pageTitle?: string
  pageSubtitle?: string
}
```

### Layout

```html
<div class="app-shell flex min-h-screen flex-col">
  <Sidebar role={role} />                  ← nav lateral fijo, 240px
  <main class="lg:ml-60">                  ← contenido principal, offset del sidebar
    <Topbar />                             ← header sticky con título + breadcrumb
    <div id="main-content"><slot /></div>  ← slot para contenido del dashboard
  </main>
  <Toast />                                ← sistema de notificaciones toast
  <LoadingOverlay />                       ← overlay de carga
  <div class="noise-overlay"></div>        ← ruido SVG (opcional, via withNoise)
</div>
```

### Scripts del DashboardShell

```js
// Chart.js se importa directamente en el script del DashboardShell (NO lazy):
// import { Chart, registerables } from 'chart.js'
// Chart.register(...registerables)
// window.Chart = Chart  ← disponible globalmente

// Render helper para gráficos con ARIA
window.renderVyntraChart = async function(canvasId, config) { ... }

// Navegación entre secciones con hash-based routing
window.initDashboardNav = function(config) {
  window.showSection = function(id) { ... }  // oculta/muestra [id^="sec-"]
  // Soporta history.pushState, hashchange, popstate
  // Dispara CustomEvent 'vyntra:navigate' para sidebar sync
}
```

---

## 7. Sidebar — navegación lateral

**Archivo:** `src/components/layout/Sidebar.astro`

### Config por rol (hardcodeada, no dinámica)

```js
const configs = {
  student: {
    label: 'Estudiante',
    accent: 'bg-gradient-to-br from-brand-maroon to-brand-maroon-dark',
    sections: [
      { id:'inicio', label:'Inicio' },
      { id:'notas', label:'Notas' },
      { id:'examenes', label:'Exámenes' },
      { id:'horarios', label:'Horarios' },
      { id:'tareas', label:'Tareas' },
      { id:'saber', label:'Pruebas Saber' },
      { id:'biblioteca', label:'Biblioteca' },
      { id:'votaciones', label:'Votaciones' },
      { id:'perfil', label:'Perfil' },
    ]
  },
  teacher: {
    sections: ['Dashboard','Control de Notas','Guías y Tareas','Exámenes','Horario','Incidentes','Alertas de Riesgo']
  },
  admin: {
    sections: ['Dashboard','Estudiantes','Docentes','Materias e IA','Avisos','Elecciones','Administradores']
  }
}
```

### Cada link del sidebar

```html
<a href="/estudiante#notas" data-section-id="notas" class="sidebar-link ...">
  <svg><!-- icono SVG inline --></svg>
  <span>Notas</span>
</a>
```

### Estado activo

```css
.sidebar-link.active {
  bg-brand-maroon/8          /* fondo claro */
  border-l-[3px] border-brand-maroon  /* indicador izquierdo */
  font-semibold
  box-shadow: inset 0 0 20px rgba(107,26,26,0.04)
}
```

### JS del Sidebar

```js
// Mobile: cierra sidebar al clickear un link
// Escucha evento 'vyntra:navigate' → actualiza aria-current y clase .active
window.addEventListener('vyntra:navigate', (e) => {
  const section = e.detail.section
  // Actualiza todos los [data-section-id]
})
```

---

## 8. Dashboard Estudiante (`/estudiante`)

**Archivo:** `src/pages/estudiante.astro`

### Wrapper

```astro
<BaseLayout withNoise={true}>
  <DashboardShell role="student" pageTitle="Panel de Estudiante">
    <WsRiskAlert />           ← WebSocket alertas de riesgo
    <AIChat role="student" /> ← Chat flotante IA
    <!-- 9 secciones con id="sec-{nombre}" -->
  </DashboardShell>
</BaseLayout>
```

### Secciones (`<section id="sec-*">`)

| ID | Sección | Contenido |
|----|---------|-----------|
| `sec-inicio` | Inicio | Welcome card (gradiente maroon), 4 stat cards, rendimiento por asignatura (barras), avisos recientes, calendario |
| `sec-notas` | Notas | Filtros P1-P4, tabla de calificaciones (materia × período), gráfico de barras bimestral, Chart.js evolución, botón exportar PDF |
| `sec-examenes` | Exámenes | Lista de exámenes disponibles, modal anti-fraude fullscreen |
| `sec-horarios` | Horarios | Tabla semanal desde API `/api/schedule` |
| `sec-tareas` | Tareas | Upload form (dropzone, select materia, título, archivo), historial de entregas |
| `sec-saber` | Pruebas Saber | 6 áreas (Matemáticas, Lenguaje, C. Naturales, C. Sociales, Inglés, ICFES), 4 bimestres, simulacro ICFES |
| `sec-biblioteca` | Biblioteca | Grid de recursos por bimestre desde API |
| `sec-votaciones` | Votaciones | Grid de candidatos, botón votar |
| `sec-perfil` | Perfil | Avatar con inicial, datos personales, resumen académico (4 stats), actividad reciente |

### JS — Inicialización

```js
var studentId = localStorage.getItem('profile_id') || localStorage.getItem('userId')
var userGrade = localStorage.getItem('userGrade')
var userName = localStorage.getItem('userName')

// Sidebar: actualiza nombre y metadata
document.getElementById('sidebar-username-student').textContent = userName
document.getElementById('sidebar-metadata-student').textContent = userGrade

// Navegación con carga lazy
window.initDashboardNav({
  titles: { inicio:'Inicio', notas:'Notas', ... },
  subs: { inicio:'Panel de rendimiento', ... },
  onSection: function(id) {
    if (id === 'notas') { loadGrades(); loadChartData() }
    if (id === 'examenes') loadExams()
    // ... carga lazy por sección
  }
})
```

### API endpoints usados por estudiante

```
GET  /api/grades?student_id=X           ← todas las notas
GET  /api/exams?student_grade=X         ← exámenes disponibles
GET  /api/schedule?student_id=X         ← horario semanal
GET  /api/students/X/homework           ← historial de tareas
POST /api/students/X/homework           ← subir tarea (FormData)
GET  /api/notices                       ← avisos/comunicados
GET  /api/admin/candidates              ← candidatos votación
POST /api/vote                          ← emitir voto
GET  /api/grades/download-pdf?student_id=X  ← boletín PDF
GET  /api/subjects                      ← materias (para selects)
GET  /api/students/X/financial-status   ← estado financiero
```

### WebSocket — Alertas de riesgo

```astro
<WsRiskAlert />  ← componente que conecta a wss://sie-8agt.onrender.com/ws?token=JWT
```

### Chat IA flotante

```astro
<AIChat role="student" />
<!-- endpoint: /api/ai/student-tutor -->
<!-- SSE streaming, localStorage persistence, sugerencias contextuales -->
```

---

## 9. Design Tokens (theme.css)

**Archivo:** `src/styles/theme.css`

### Paleta de color — VALORES INTENCIONALES

> ⚠️ **⚠️ IMPORTANTE**: Las siguientes variables CSS están documentadas como diseño intencional pero **NO están definidas en el `theme.css` real**. Esto es un bug conocido (E1-E3 en `docs/bugs.md`). En el código real, `--bg`, `--text`, `--brand-maroon`, `--brand-gold`, `--solar-cream` etc. NO existen como CSS vars. Usar clases Tailwind (`bg-brand-maroon`, `text-brand-gold`) para colores, no `var()`.

```css
:root {
  /* Solar base */
  --solar-cream: #FFFBF0;    /* ❌ No definido en theme.css real */
  --solar-gold: #F5A623;     /* ❌ No definido en theme.css real */

  /* Brand */
  --brand-maroon: #6B1A1A;       /* ❌ No definido en theme.css real */
  --brand-maroon-light: #8B2A2A; /* ❌ No definido */
  --brand-maroon-dark: #4A0E0E;  /* ❌ No definido */
  --brand-gold: #F5A623;         /* ❌ No definido */
  --brand-gold-light: #FFD166;   /* ❌ No definido */

  /* Light theme */
  --bg: #FFFBF0;             /* ❌ No definido en theme.css real */
  --bg-secondary: #FFF8E7;   /* ❌ No definido */
  --text: #2D1B0A;           /* ❌ No definido */
  --text-secondary: #7A6254; /* ❌ No definido */

  /* These DO exist in real theme.css: */
  --text-tertiary: #7A6050;
  --border: rgba(107,26,26,0.06);
  --success: #34D399; --danger: #DC2626;
  --info: #3B82F6; --warning: #F5A623;
  --space-1..20; --text-body/h1/h2/h3;
}
```

### Keyframes globales

```css
@keyframes shimmer      → skeleton loading
@keyframes fadeUp       → scroll reveals (translateY 20→0)
@keyframes sectionEnter → transiciones de sección dashboard
@keyframes toastSlideIn → notificaciones toast
@keyframes float-up     → partículas flotantes (login)
@keyframes breathe      → pulso de glow
@keyframes logo-breathe → pulso del logo con drop-shadow
@keyframes star         → twinkle de partículas
```

### Accesibilidad

```css
/* Reduced motion: detiene TODAS las animaciones */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus visible: anillo dorado */
:focus-visible {
  outline: 2px solid var(--brand-gold);
  outline-offset: 2px;
}

/* Touch targets: mínimo 44×44px en mobile */
button, a[role="button"], [onclick] {
  min-width: 44px; min-height: 44px;  /* mobile only via @media */
}
```

---

## 10. Flujo de autenticación

```
1. Usuario llega a /login
2. Ingresa credential + password
3. POST /api/auth/login → backend responde con:
   - Set-Cookie: httpOnly (auth cookie principal)
   - JSON: { access_token, usuario: { rol, nombre, profile_id }, grado }
4. Frontend guarda en localStorage:
   - ws_access_token (solo para WebSocket)
   - userRole, userName, userId, profile_id, userGrade
5. Redirect según rol: /estudiante, /docente, /admin
6. Session Manager (BaseLayout inline) intercepta todos los fetch/XHR:
   - Si 401 Y userId existía → clear + redirect /login
   - Si 401 SIN userId → ignora (no había sesión)
```

---

## 11. Componentes UI compartidos

| Componente | Ubicación | Función |
|-----------|-----------|---------|
| `Logo.astro` | `src/components/` | SVG del sol + libro, props size/animated/class |
| `Toast.astro` | `src/components/ui/` | Sistema toast (success/error/warning/info), `window.VyntraToast` |
| `LoadingOverlay.astro` | `src/components/ui/` | Overlay de carga con spinner |
| `AIChat.astro` | `src/components/` | Chat flotante SSE streaming, 3 roles |
| `WsRiskAlert.astro` | `src/components/` | WebSocket alertas + audio Web Audio API |
| `SEOHead.astro` | `src/components/` | Meta tags adicionales |
