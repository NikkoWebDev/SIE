# VYNTRA Academic — Agent Guide

## Project Overview
Full-stack Academic Platform (VYNTRA Solaris v5.0) — Sogamoso, Boyacá, Colombia.
- **Framework**: Astro v5 (static + serverless SSR)
- **UI**: Tailwind CSS v3 + CSS design tokens (`src/styles/theme.css`)
- **Deployment**: Netlify (primary) + Vercel (secondary)
- **Backend**: FastAPI (Python, hosted on Render)
- **Database**: Supabase (Postgres)
- **Auth**: JWT (stored in localStorage)
- **AI**: OpenRouter API streaming chat (VYNTRA Tutor)

## Design System — "Solar Technocratic"

### Theme
- **Dual theme**: Light (`#FFFBF0` — solar cream) and Dark (`#0D0A08` — warm charcoal)
- **Toggle**: Class-based on `<html>`, persisted to `localStorage('vyntra-theme')`, respects `prefers-color-scheme`
- **Brand colors**: Maroon `#6B1A1A`, Gold `#F5A623`, Solar Amber `#FF8C00`
- **Typography**: Fraunces (display headings), DM Sans (body), Syne (accent), Azeret Mono (data/technical)
- **Atmosphere**: CSS noise overlay (SVG fractalNoise), solar orbs, grid dots, construction diagram SVGs
- **Motion**: Staggered reveals (IntersectionObserver), spring easing, section-enter animations, toast slide-in

### Shared CSS (`src/styles/theme.css`)
- **Design tokens**: CSS custom properties for bg, text, border, shadow, glass, input, skeleton, scrollbar, glow
- **Section transitions**: `.section-enter` / `.section-enter-fast` — fade+slide-up on dashboard navigation
- **Sidebar glow**: Active section indicator with inset box-shadow
- **Solar flare**: Radial gradient overlay for hero sections
- **Skeleton variants**: `skeleton-shimmer` (basic), `skeleton-table-row`, `skeleton-card`, `skeleton-stat`
- **Responsive**: Table overflow wrappers, full-width mobile toasts, 44px touch targets (≤640px)
- **Accessibility**: `:focus-visible` gold ring, `prefers-reduced-motion` disable, `::selection` maroon/gold

### Component Architecture
- **BaseLayout.astro** — Root layout: CSP headers, SEO meta, Google Fonts, theme init script, noise overlay, `window.__API_URL__`
- **DashboardShell.astro** — Unified dashboard wrapper: Sidebar + Topbar + Toast + LoadingOverlay + shared dashboard lib (inline)
- **Sidebar.astro** — Role-aware sidebar (student/teacher/admin), hardcoded navigation configs, mobile overlay, theme toggle, logout
- **Topbar.astro** — Responsive topbar with hamburger menu, live breadcrumb, user avatar
- **AIChat.astro** — Floating chat bubble, 3 role configs, SSE streaming, localStorage persistence, contextual suggestions
- **WsRiskAlert.astro** — WebSocket client, audio alerts (Web Audio API), slide-in toast
- **UI components**: Button, Card, Input, Badge, Modal, Toast, Skeleton, LoadingOverlay

### Pages

#### Public
- **`index.astro`** — Landing page. Solar particles canvas, animated orbs, grid dots, construction SVG lines, staggered reveals (IntersectionObserver), 4-stat grid from API, 3 features, notices grid, footer.
- **`login.astro`** — Split panel (45/55), solar glow + construction diagrams, segmented role tab (Estudiante/Personal) with spring slider, input focus glow, forgot password modal 2-step flow.
- **`dashboard.astro`** — Role-based redirect. Reads `userRole` from localStorage, routes to `/estudiante`, `/docente`, or `/admin`.

#### Dashboards (all use BaseLayout + DashboardShell + Sidebar + Topbar)
- **`estudiante.astro`** — 9 sections: Inicio, Notas (Chart.js), Exámenes (anti-fraud modal), Horarios, Tareas, Pruebas Saber (6 areas × 4 bimestres), Biblioteca, Votaciones, Perfil. Includes WsRiskAlert + AIChat.
- **`docente.astro`** — 7 sections: Dashboard stats, Control de Notas (P1-P4 planilla with auto-average), Guías y Tareas (upload + inbox), Exámenes (question builder), Horario, Incidentes de Seguridad, Alertas de Riesgo.
- **`admin.astro`** — 7 sections: Dashboard stats, Gestión de Alumnos (CRUD + filters + CSV export), Cuerpo Docente, Materias e IA, Avisos, Elecciones (Chart.js), Administradores. Includes modal forms for CRUD.

#### Shared
- **`AIChat.astro`** — Inline SSE streaming chat, 3 role configs, typing indicator, localStorage persistence, contextual suggestion chips. Loaded on all 3 dashboards.
- **`WsRiskAlert.astro`** — WebSocket risk alert client, audio + toast notifications, auto-dismiss. Loaded on student dashboard.
- **404.astro** — Solar eclipse themed error page.

## API Integration
- **Auth**: `POST /api/auth/login` → JWT token → localStorage (`access_token`, `userId`, `userRole`, `userName`)
- **Grades**: `GET /api/grades?student_id=X`, `GET /api/grades?teacher_id=X`, `POST /api/teacher/submit-grade`
- **Financial**: `GET /api/students/X/financial-status`, `PATCH /api/admin/students/X/financial`
- **Risk**: `GET /api/students/risk`, WebSocket at `ws://.../ws?token=JWT`
- **Notices**: `GET /api/notices`, `POST /api/admin/notices`
- **Stats**: `GET /api/admin/stats`
- **Candidates**: `GET/POST/DELETE /api/admin/candidates`, `POST /api/admin/election-reset`
- **AI**: `POST /api/ai/student-tutor`, `POST /api/ai/teacher-tutor`, `POST /api/ai/admin-assistant` (SSE streaming)
- **PDF**: `GET /api/grades/download-pdf?student_id=X`
- **URL**: Centralized via `import.meta.env.PUBLIC_API_URL` (set in `.env` local, `netlify.toml` deploy)

## Build & Run
```bash
npm install          # Install dependencies (includes terser + lightningcss for minification)
npm run dev          # astro dev
npm run build        # astro build
npm run preview      # astro preview
```

## Conventions
1. All dashboard pages use `BaseLayout` + `<DashboardShell role={role}>` wrapper pattern
2. `Sidebar.astro` uses `define:vars` for role-specific IDs (sidebar-username-{role}, sidebar-metadata-{role})
3. Theme toggle: `window.setVyntraTheme(dark)` available via shared dashboard lib
4. API calls: use inline `fetch` with `Authorization: Bearer ${token}` header; 401 → redirect
5. Error handling: use `window.VyntraToast?.error()` (available on all DashboardShell pages)
6. Section navigation: `window.showSection(id)` — dispatches `vyntra:navigate` CustomEvent for sidebar sync
7. Fonts: loaded from Google Fonts CDN in BaseLayout `<head>`; use Tailwind font classes
8. CSS: all styling via Tailwind utilities; theme tokens only in CSS custom properties
9. Responsive: 6 breakpoints (xs:380px through 2xl:1440px), mobile-first, 44px touch targets
10. Animation: `prefers-reduced-motion` disables all animations, `section-enter` for dashboard transitions
11. Security: VyntraToast HTML-escapes messages, login uses `.textContent` not `.innerHTML`, CDN scripts use SRI integrity
