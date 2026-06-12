# VYNTRA Academic — Agent Guide

> ⚠️ **IMPORTANTE**: `C_sol/claude.md` es la referencia autoritaria. Este archivo es un resumen complementario. Si hay conflicto, prevalece `claude.md`.

## Project Overview
Full-stack Academic Platform (VYNTRA Solaris v5.0) — Sogamoso, Boyacá, Colombia.
- **Framework**: Astro v5 (SSG)
- **UI**: Tailwind CSS v3 + CSS design tokens (`src/styles/theme.css`)
- **Deployment**: Netlify (static, redirects to Render backend)
- **Backend**: FastAPI (Python, hosted on Render)
- **Database**: Supabase (Postgres)
- **Auth**: JWT HS256 — Bearer header (primary for API) + httpOnly cookie (`credentials: 'include'`). `ws_access_token` in localStorage only for WebSocket.
- **AI**: OpenRouter API streaming chat (VYNTRA Tutor)

## Design System — "Solar Technocratic"

### Theme
- **Dual theme**: Light (`#FFFBF0` — solar cream) and Dark (`#0D0A08` — warm charcoal)
- **Toggle**: Class-based on `<html>`, persisted to `localStorage('vyntra-theme')`, respects `prefers-color-scheme`
- **Brand colors**: Maroon `#6B1A1A`, Gold `#F5A623`, Solar Amber `#FF8C00`
- **Typography**: Fraunces (display headings), DM Sans (body), Syne (accent), Azeret Mono (data/technical)
- **Atmosphere**: CSS noise overlay (SVG fractalNoise), solar orbs, grid dots
- **Motion**: GSAP ScrollTrigger (landing), spring easing, section-enter animations, toast slide-in

### Shared CSS (`src/styles/theme.css`)
- **Design tokens**: CSS custom properties for border, shadow, glass, input, skeleton, scrollbar, glow
- **⚠️ Missing vars**: `--bg`, `--text`, `--bg-card`, `--bg-secondary`, `--solar-cream`, `--brand-maroon`, `--brand-gold` are referenced but NEVER defined in `:root` or `.dark`. Tailwind classes (`bg-brand-maroon`) work fine; direct `var()` references don't.
- **Section transitions**: `.section-enter` / `.section-enter-fast` — fade+slide-up on dashboard navigation
- **Sidebar glow**: Active section indicator with inset box-shadow
- **Skeleton variants**: `skeleton-shimmer` (basic), `skeleton-table-row`, `skeleton-card`, `skeleton-stat`
- **Responsive**: Table overflow wrappers, full-width mobile toasts, 44px touch targets (≤640px)
- **Accessibility**: `:focus-visible` gold ring, `prefers-reduced-motion` disable, `::selection` maroon/gold

### Component Architecture
- **BaseLayout.astro** — Root layout: CSP headers, SEO meta, Google Fonts, theme init script, noise overlay, `window.__API_URL__`, session manager, `vfetch()`, auth interceptor
- **DashboardShell.astro** — Unified dashboard wrapper: Sidebar + Topbar + Toast + LoadingOverlay + Chart.js lazy load
- **Sidebar.astro** — Role-aware sidebar (student/teacher/admin), hardcoded navigation configs, mobile overlay, theme toggle, logout
- **Topbar.astro** — Responsive topbar with hamburger menu, live breadcrumb, user avatar, live clock
- **AIChat.astro** — Floating chat bubble, 3 role configs, SSE streaming, localStorage persistence, contextual suggestions
- **WsRiskAlert.astro** — WebSocket client, audio alerts (Web Audio API), slide-in toast
- **UI components**: Toast, LoadingOverlay, Logo

### Pages

#### Public
- **`index.astro`** — Landing page. GSAP ScrollTrigger solar journey (410vh), single Logo travels screen, 4 stat cards, 6 features, notices grid, CTA. Mode claro exclusivo.
- **`login.astro`** — Compact centered layout (no split panel, no role tabs). Single form: credential + password. Logo as crown jewel. Forgot password modal 2-step flow. Uses `BaseLayout`.
- **`dashboard.astro`** — Role-based redirect. Reads `userRole` from localStorage, routes to `/estudiante`, `/docente`, or `/admin`.

#### Dashboards (all use BaseLayout + DashboardShell + Sidebar + Topbar)
- **`estudiante.astro`** — 9 sections: Inicio, Notas (Chart.js), Exámenes (anti-fraud modal), Horarios, Tareas, Pruebas Saber (6 areas × 4 bimestres), Biblioteca, Votaciones, Perfil. Includes WsRiskAlert + AIChat.
- **`docente.astro`** — 7 sections: Dashboard stats, Control de Notas (P1-P4 planilla with auto-average), Guías y Tareas (upload + inbox), Exámenes (question builder), Horario, Incidentes de Seguridad, Alertas de Riesgo.
- **`admin.astro`** — 7 sections: Dashboard stats, Gestión de Alumnos (CRUD + filters + CSV export), Cuerpo Docente, Materias e IA, Avisos, Elecciones (Chart.js), Administradores. Includes modal forms for CRUD.

#### Shared
- **`AIChat.astro`** — Inline SSE streaming chat, 3 role configs, typing indicator, localStorage persistence, contextual suggestion chips. Loaded on all 3 dashboards.
- **`WsRiskAlert.astro`** — WebSocket risk alert client, audio + toast notifications, auto-dismiss. Loaded on student dashboard.
- **404.astro** — Solar eclipse themed error page.

### Layout wrappers (CORRECT)
```
BaseLayout.astro ← RAÍZ: CSP, SEO, fonts, session, theme, vfetch, auth interceptor
  ├── Páginas públicas (index, login, 404)
  └── DashboardShell.astro ← Sidebar + Topbar + Toast + Loading + Chart.js
        └── Sidebar.astro + Topbar.astro
        └── Dashboards (estudiante, docente, admin)
```
❌ `Layout.astro` NO es usado por ninguna página actual.
❌ `public/js/session.js` NO es cargado por BaseLayout (solo Layout.astro legacy lo incluye).

## API Integration
- **Backend URL**: `https://sie-8agt.onrender.com` (canonical)
- **Auth**: `POST /api/auth/login` → backend sets httpOnly `Set-Cookie` + returns `access_token` in JSON body. Frontend stores `ws_access_token` (WebSocket only), `userId`, `userRole` in localStorage. API calls use `credentials: 'include'` (cookie auth).
- **Grades**: `GET /api/grades?student_id=X`, `GET /api/grades?teacher_id=X`, `POST /api/teacher/submit-grade`
- **Financial**: `GET /api/students/X/financial-status`, `PATCH /api/admin/students/X/financial`
- **Risk**: `GET /api/students/risk`, WebSocket at `wss://sie-8agt.onrender.com/ws?token=JWT`
- **Notices**: `GET /api/notices`, `POST /api/admin/notices`
- **Stats**: `GET /api/admin/stats`
- **Candidates**: `GET/POST/DELETE /api/admin/candidates`, `POST /api/admin/election-reset`
- **AI**: `POST /api/ai/student-tutor`, `POST /api/ai/teacher-tutor`, `POST /api/ai/admin-assistant` (SSE streaming)
- **PDF**: `GET /api/grades/download-pdf?student_id=X`
- **URL**: Set via `import.meta.env.PUBLIC_API_URL` (`.env` local, Netlify build env)

## Build & Run
```bash
npm install          # Install dependencies (includes terser + lightningcss for minification)
npm run dev          # astro dev
npm run build        # astro build
npm run preview      # astro preview
npm run test         # playwright test --project=ci
npm run test:backend # cd backend && python3 -m pytest tests/ -v
```

## Conventions
1. All dashboard pages use `BaseLayout` + `<DashboardShell role={role}>` wrapper pattern
2. Sidebar IDs: `sidebar-username-{role}`, `sidebar-metadata-{role}` (set via inline JS, not `define:vars`)
3. Theme toggle: `window.setVyntraTheme(dark)` available via BaseLayout inline script
4. API calls: use `window.vfetch()` with `credentials: 'include'` (cookie auth); 401 → toast + redirect
5. Error handling: use `window.VyntraToast?.error()` (available on all DashboardShell pages)
6. Section navigation: `window.showSection(id)` — dispatches `vyntra:navigate` CustomEvent for sidebar sync
7. Fonts: loaded from Google Fonts CDN in BaseLayout `<head>`; use Tailwind font classes
8. CSS: all styling via Tailwind utilities; theme tokens only in CSS custom properties. ⚠️ Use Tailwind classes for brand colors (`bg-brand-maroon`, `text-brand-gold`), NOT `var(--brand-*)` which aren't defined.
9. Responsive: 6 breakpoints (xs:380px through 2xl:1440px), mobile-first, 44px touch targets
10. Animation: `prefers-reduced-motion` disables all animations, `section-enter` for dashboard transitions
11. Security: Use `window.escapeHtml()` for any dynamic text. NEVER `innerHTML` with interpolated data.

## Known Issues (Quick Reference)
→ Full list: `docs/bugs.md` (33+ issues) and `C_sol/claude.md#11-bugs-conocidos`
- **E1-E3**: CSS vars `--bg`, `--text`, `--brand-maroon`, `--brand-gold` undefined → dark mode broken. Fix by defining in `:root` + `.dark`.
- **E5**: XSS in `index.astro` — notices use `innerHTML` without escape
- **E6**: Teacher grade sheet: subject select never populates → planilla inoperable
- **E9**: `backend/models/academic.py` imports `bson` (MongoDB) → crash if imported
- **E14**: Password reset generates code but never delivers it to user
- **E15**: E2E test credentials don't match seed.sql data

## Files that DON'T exist (despite being documented)
- `src/scripts/api.ts` ❌ — use `window.vfetch()` instead
- `src/config.ts` ❌
- `src/lib/utils.ts` ❌
- `apiFetch()` function ❌ — use `vfetch()` or fetch with `credentials: 'include'`
- `vfetchJSON()` function ❌ — use `vfetch()` then `.json()` manually
- `ARCHITECTURE.md`, `FRONTEND.md` ❌ — never existed
