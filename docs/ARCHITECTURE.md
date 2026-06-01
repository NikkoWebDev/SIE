# VYNTRA Academic — Architecture

## Overview
Full-stack academic platform for Colegio Técnico Ciudad del Sol (Sogamoso, Boyacá, Colombia).
- **Frontend**: Astro v5 (SSG) deployed on Netlify
- **Backend**: FastAPI (Python) deployed on Render
- **Database**: Supabase (Postgres)
- **Auth**: Custom JWT (bcrypt) for students/legacy + Supabase Auth (Google OAuth for teachers)
- **AI**: OpenRouter API streaming via VYNTRA Tutor agents

## Domain
- `https://vyntraacademic.netlify.app` (Netlify, production)
- `https://colegiociudaddelsol.edu.co` (final domain TBD)

## Key Design Decisions
- Apple-inspired dark/light theme (black `#000` bg dark, white `#fff` bg light)
- Brand colors: Maroon `#800000`, Gold `#FDC003`
- Syne (display) + Sora (body) fonts
- CSS noise overlay + grid dots for atmosphere
- Unified CSS design system in `src/styles/theme.css`

## Directory Structure
```
Vyntra/
├── src/
│   ├── pages/          # Astro pages (routing)
│   │   ├── index.astro       # Landing page
│   │   ├── login.astro       # Login (split panel, segmented tabs)
│   │   ├── dashboard.astro   # Auth redirect router
│   │   ├── estudiante.astro  # Student dashboard
│   │   ├── docente.astro     # Teacher dashboard
│   │   ├── admin.astro       # Admin dashboard
│   │   └── 404.astro         # 404 page
│   ├── components/           # Astro components
│   │   ├── AIChat.astro      # AI tutor (role-based)
│   │   ├── WsRiskAlert.astro # WebSocket risk alerts
│   │   ├── SEOHead.astro     # SEO/Schema.org meta
│   │   └── ...
│   ├── layouts/
│   │   └── Layout.astro      # Shell with sidebar + topbar
│   ├── styles/
│   │   └── theme.css         # Design system (all CSS vars + utilities)
│   └── assets/
│       └── brand/            # Logo assets
├── backend/
│   ├── main.py               # FastAPI entry point
│   ├── dependencies.py       # JWT auth, guards, deps
│   ├── config/
│   │   └── database.py       # Supabase client init
│   ├── models/               # Pydantic models
│   │   ├── auth.py           # Auth schemas
│   │   └── schemas.py        # All domain schemas
│   ├── routers/
│   │   ├── auth.py           # Login, register, OAuth
│   │   ├── admin.py          # Admin endpoints
│   │   ├── teachers.py       # Teacher endpoints + upload
│   │   ├── students.py       # Student data endpoints
│   │   ├── exams.py          # Exam + risk alerts
│   │   ├── grades.py         # Grade queries
│   │   ├── subjects.py       # Subject queries
│   │   └── ai_agent.py       # AI chat (3 roles)
│   ├── google_drive.py       # Google Drive upload module
│   ├── migrations/           # SQL migrations
│   ├── tests/                # Pytest suite
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── public/
│   ├── js/session.js         # Auth check + auto-logout
│   └── _redirects            # Netlify SPA fallback
├── netlify.toml
├── astro.config.mjs
└── package.json
```

## Data Flow
1. User visits Netlify → Astro serves static HTML
2. Frontend JS fetches from Render `/api/*`
3. Backend queries Supabase → returns JSON
4. Auth: JWT in localStorage, sent as Bearer header
5. Real-time alerts: WebSocket to Render `/ws`
6. AI tutor: SSE streaming from OpenRouter via Render
