# VYNTRA Academic — Agent Guide

## Project Overview
Full-stack Academic Platform (VYNTRA) — Sogamoso, Boyacá, Colombia.
- **Framework**: Astro v5 (static site generation)
- **UI**: Unified CSS design system (`src/styles/theme.css`) + Tailwind v3 (layout utilities only)
- **Deployment**: Vercel (static + serverless)
- **Backend**: FastAPI (Python, hosted on Render)
- **Database**: Supabase (Postgres)
- **Auth**: JWT (stored in localStorage)
- **AI**: OpenRouter API streaming chat (VYNTRA Tutor)

## Design System — "Apple Editorial"

### Theme
- **Dual theme**: Light (`#ffffff` bg) and Dark (`#000000` bg)
- **Toggle**: Class-based on `<html>`, persisted to `localStorage('vyntra-theme')`, respects `prefers-color-scheme`
- **Brand colors**: Maroon `#800000`, Gold `#FDC003`, colors used as accents only — background is always neutral
- **Typography**: Syne (display headings), Sora (body) — loaded from Google Fonts via `<link>` in Layout.astro `<head>`
- **Atmosphere**: Subtle CSS noise overlay (SVG fractalNoise, 1.5% opacity), grid dots background on hero pages

### Shared CSS (`src/styles/theme.css`)
- **Design tokens**: CSS custom properties for spacing, radius, easing, colors, shadows
- **Cards**: `.card-float` — white/black bg, subtle border, shadow, hover elevation
- **Inputs**: `.input-apple` — minimal border, focus ring in maroon
- **Buttons**: `.btn-apple` + `.btn-primary|secondary|ghost|gold` — spring scale on active
- **Glass**: `.glass` + `.nav-blur` — backdrop-filter blur for nav/topbar
- **Skeleton**: `.shimmer` — animated gradient shimmer for loading states
- **Badge**: `.badge` + `.badge-maroon|gold|green|red` — pill labels
- **Sidebar**: `.sidebar` — fixed left, 240px, responsive overlay on mobile
- **Topbar**: `.topbar` — sticky, blur backdrop, border-bottom
- **Stats**: `.stats-grid` + `.stat-card` + `.stat-value` — auto-fit grid
- **Tabs**: `.tab-bar` + `.tab-btn` — border-bottom active indicator

## Pages

### Public
- **`index.astro`** — Landing page. Lightweight hero with grid dots and subtle maroon orb, stats grid, feature cards, notices section. Dual theme.
- **`login.astro`** — Split layout: left 45% brand panel, right 55% Apple-style form. Segmented tab control (Estudiante / Personal). JWT auth. Dual theme.
- **`dashboard.astro`** — Auth-based redirect page. Reads `userRole` from localStorage, routes to `/estudiante`, `/docente`, or `/admin`.

### Dashboards (all use `Layout.astro` with sidebar)
- **`estudiante.astro`** — Student panel. Academic grades grid, ABP hub with tabs (parciales + proyecto transversal drag-drop), grade cards with progress bars. Uses `AIChat` + `WsRiskAlert`.
- **`docente.astro`** — Teacher standalone sidebar. Grade entry form, recent grades list, risk alerts feed. Uses jsPDF for reports.
- **`admin.astro`** — Rector/admin standalone sidebar. Student management table with filters/CSV export, teacher management, subjects config with AI links, notices publish, election management with Chart.js.

### Shared layout
- **`Layout.astro`** — Base HTML shell with theme injection, sidebar nav, glass topbar, content area. Used by `estudiante.astro` and `dashboard.astro`.
- **`Sidebar.astro`** (used by `admin.astro` and `docente.astro`) — Standalone sidebar component with nav links, user badge, theme toggle.

### Components
- **`WsRiskAlert.astro`** — WebSocket client for real-time risk alerts. Fixed top-right toast notifications. Audio alert (Web Audio API oscillator).
- **`AIChat.astro`** — Role-based AI tutor. Supports student/teacher/admin roles via `role` prop. Streaming SSE chat. Context-aware (grades, risk status, financial state). Uses CSS custom properties for accent colors.

## AI System (VYNTRA Tutor)

### Backend (`backend/routers/ai_agent.py`)
- **Router**: `/api/ai`, tags: `["ai"]`
- **3 endpoints**, each with role-specific system prompt, API key, temperature, and max_tokens:

| Endpoint | Auth | API Key | Temperature | Max Tokens | Prompt |
|---|---|---|---|---|---|
| `POST /api/ai/student-tutor` | `auth_dependency` | `OPENROUTER_STUDENT_KEY` | 0.7 | 1024 | Empathic tutor for ABP subjects |
| `POST /api/ai/teacher-tutor` | `teacher_dependency` | `OPENROUTER_TEACHER_KEY` | 0.6 | 2048 | Analytical assistant for pedagogy |
| `POST /api/ai/admin-assistant` | `admin_dependency` | `OPENROUTER_ADMIN_KEY` | 0.5 | 2048 | Executive advisor for financial strategy |

- **Model**: `OPENROUTER_MODEL` env var (default: `openrouter/free`)
- **Conversation memory**: In-memory `OrderedDict`, last 10 messages per user, capped at 1000 users
- **Streaming**: SSE via `StreamingResponse`, each token yielded as `data: {"token": "..."}`
- **Error handling**: Logged with role, user_id, and status code; client receives SSE error event

### Role-based Auth Dependencies (`backend/dependencies.py`)
- `auth_dependency` — Validates JWT, sets `request.state.user_role`, returns `sub`
- `teacher_dependency` — Calls `auth_dependency`, validates role is `teacher`/`profesor`
- `admin_dependency` — Calls `auth_dependency`, validates role is `admin`/`rector`

### Docker Compose (`backend/docker-compose.yml`)
- Requires: `OPENROUTER_STUDENT_KEY`, `OPENROUTER_TEACHER_KEY`, `OPENROUTER_ADMIN_KEY`, `OPENROUTER_MODEL`

## API Integration
- **Auth**: `POST /api/auth/login` → JWT token stored in localStorage (fields: `access_token`, `userId`, `userRole`, `userName`)
- **Grades**: `GET /api/grades?student_id=X`, `GET /api/grades?teacher_id=X`, `POST /api/teacher/submit-grade`
- **Financial**: `GET /api/students/X/financial-status`, `PATCH /api/admin/students/X/financial`
- **Risk**: `GET /api/students/risk` (returns `profile_id`, `fullname`, `login_credential`, `avg_score`, `status`), WebSocket at `ws://.../ws?token=JWT`
- **Notices**: `GET /api/notices`
- **Stats**: `GET /api/admin/stats`
- **PDF**: `GET /api/grades/download-pdf?student_id=X`
- **Shared fetch**: Use `apiFetch()` from `src/scripts/api.ts` for automatic 401 redirect

### DB Schema Notes
- `grades.student_id` and `grades.subject_id` are UUID columns referencing `profiles.id` and `subjects.id` respectively
- When submitting grades, the backend must resolve `login_credential` → UUID for `student_id` and subject `name` → UUID for `subject_id`
- ABP propagation: when `project_id` contains "abp" or "proyecto", the grade is copied to all subjects in `_abp_propagated_subjects`

## Build & Run
```bash
npm run dev      # astro dev
npm run build    # astro build
npm run preview  # astro preview
npm run check    # astro check (type/lint)
```

## Conventions for New Pages
1. Use `Layout.astro` (with sidebar) for student/general pages; use `Sidebar.astro` for standalone admin/docente pages
2. Include `WsRiskAlert` only on student dashboard
3. Include `AIChat` on pages needing AI assistant, pass `role` prop
4. Use CSS custom properties from `theme.css` instead of hardcoded colors
5. Use `apiFetch()` from `src/scripts/api.ts` for all API calls
6. Auth check: redirect to `/login` if no token
7. Fonts: always use `font-family: var(--font-body)` or `var(--font-display)` CSS vars
8. Theme: support both light and dark modes via `var(--bg)`, `var(--text)`, etc.
