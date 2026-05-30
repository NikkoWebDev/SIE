# C sol SIE — Agent Guide

## Project Overview
Full-stack Student Information System (SIE) for Colegio Técnico Ciudad del Sol, Sogamoso, Boyacá, Colombia.
- **Framework**: Astro v5 (static site generation)
- **UI**: Tailwind CSS v3 + custom CSS
- **Deployment**: Vercel (static + serverless)
- **Backend**: FastAPI (Python, hosted on Render)
- **Database**: Supabase (Postgres)
- **Auth**: JWT (stored in localStorage)
- **AI**: OpenRouter API streaming chat (VYNTRA Tutor)

## Design System — "Solar Command Center"

### Theme
- **Always dark**: `#040405` background, `#0A0A0E` near-black
- **Brand colors**: Maroon `#800000`, Gold `#FDC003`, Emerald `#34D399`, Green `#4caf50`, Danger `#BA1A1A`
- **Typography**: Syne (headings), Sora (body) — loaded from Google Fonts
- **Atmosphere**: Noise texture overlay (SVG fractalNoise, 2% opacity), grid background (60px cells, masked radial gradient), solar corona glow (pulsing radial gradient), orbital rings (rotating `::before`/`::after` borders with orbiting dots)

### Shared CSS patterns
- **Glass cards**: `background: rgba(255,255,255,0.03); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.06); border-radius: 1.5rem;`
- **Inputs**: `background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08);` Gold focus ring
- **Shimmer skeletons**: `linear-gradient(90deg, transparent 0%, rgba(128,0,0,0.08) 50%, transparent 100%)` with 2s infinite animation
- **Scrollbar**: 6px wide, maroon thumb, transparent track
- **Animations**: `--ease-out-expo: cubic-bezier(0.19, 1, 0.22, 1); --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);`

## Pages

### Public
- **`index.astro`** — Landing page. Hero section with solar ring, orbiting dots, stats grid, institutional cards, notices section.
- **`login.astro`** — Split layout: left 45% brand panel (solar corona + orbit animations), right 55% login form (glass card). Segmented tab control (Estudiante / Personal). JWT auth.

### Dashboards (all use `sinMenu` on Layout + FloatingPillNav)
- **`estudiante.astro`** — Student panel. Academic grades with SVG score ring, subject cards with progress bars, schedule timeline, financial status card, quick actions (PDF download, AI tutor). Uses `AIChat`.
- **`docente.astro`** — Teacher panel. Grade entry form (dark glass inputs), recent grades list, risk alerts feed. Uses `AIChatTeacher`.
- **`admin.astro`** — Rector/admin panel. Student financial list with toggle switches, financial summary with progress bars (paid/unpaid), system status. Uses `AIChatAdmin`.

### Shared layout
- **`Layout.astro`** — Base HTML shell with SEOHead, dark theme class injection, sidebar (only when `!sinMenu`).
- **`FloatingPillNav.astro`** — Bottom nav on mobile, left sidebar on desktop (`lg:w-64`). Dark glass background. Role-based nav items. Premium-locked items for students in debt.

### Components
- **`WsRiskAlert.astro`** — WebSocket client for real-time risk alerts. Fixed top-right toast notifications. Audio alert (Web Audio API oscillator).
- **`AIChat.astro`** — Student AI tutor (maroon, calls `/api/ai/student-tutor`).
- **`AIChatTeacher.astro`** — Teacher AI assistant (green, calls `/api/ai/teacher-tutor`). Context: recent grade count, at-risk students.
- **`AIChatAdmin.astro`** — Admin AI assistant (gold/amber, calls `/api/ai/admin-assistant`). Context: financial stats, paid/unpaid counts.
- **`ScoreOrbital.astro`** — SVG ring score display (green/amber/red).
- **`PerformanceBadge.astro`** — Color-coded badge (Sobresaliente/Aceptable/En Riesgo).
- **`MetricCard.astro`** — Score card with progress bar.
- **`DangerAlert.astro`** — Dismissible risk alert banner.

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

### DB Schema Notes
- `grades.student_id` and `grades.subject_id` are UUID columns referencing `profiles.id` and `subjects.id` respectively
- When submitting grades, the backend must resolve `login_credential` → UUID for `student_id` and subject `name` → UUID for `subject_id`
- ABP propagation: when `project_id` contains "abp" or "proyecto", the grade is copied to all subjects in `_abp_propagated_subjects`

## Build & Run
```bash
npm run dev      # astro dev
npm run build    # astro build
npm run preview  # astro preview
```

## Conventions for New Pages
1. Use `Layout` with `sinMenu` for full-page dark dashboards
2. Include `FloatingPillNav`, `WsRiskAlert`, and the appropriate `AIChat*` component
3. Use the shared CSS patterns (glass-card, shimmer, noise overlay, solar-glow, etc.)
4. Keep the dark solar aesthetic: no light backgrounds, no Inter/Roboto fonts
5. Auth check at top of every script: redirect to `/` if no token
6. When displaying `student_id` or `subject_id` from grades, resolve UUIDs to human-readable names via API lookups
7. Risk alert fields in the frontend use `s.fullname` and `s.profile_id`, NOT legacy names like `s.nombre` or `s._id`
