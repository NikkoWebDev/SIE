# VYNTRA Solaris v5.0 — Consolidated Documentation

This is a streamlined version of the project documentation that combines the most essential information from various documentation files.

## Core Project Information

**Project**: VYNTRA Academic (Solaris v5.0)
**Institution**: Colegio Técnico Ciudad del Sol — Sogamoso, Boyacá, Colombia
**Methodology**: ABP (Aprendizaje Basado en Proyectos)
**Final URL**: `https://colegiociudaddelsol.edu.co`
**Current URL**: `https://vyntraacademic.netlify.app`

## Technology Stack

- **Frontend**: Astro v5.7 (SSG) + Tailwind CSS v3.4
- **Backend**: FastAPI (Python 3.12+) + Supabase (PostgreSQL)
- **Authentication**: JWT HS256 + CSRF Double Submit Cookie
- **AI**: OpenRouter API streaming
- **Deployment**: Netlify (frontend) + Render (backend)

## Key Files Structure

```
C_sol/
├── claude.md                   ← Main authoritative reference
├── Vyntra/                     
│   ├── docs/                   
│   │   ├── bugs.md              ← Active bugs tracking
│   │   ├── concepto_diseño.md   ← Design system
│   │   └── plans/               ← Implementation plans
└── _archive/legacy/             ← Legacy code (v0.5)
```

## Hosting & Architecture

- **Frontend**: Netlify (Static SSG, redirects to Render for API)
- **Backend API**: Render (Free tier → cold starts)
- **Database**: Supabase Cloud (PostgreSQL)
- **Files**: Cloudinary (images/docs) + Google Drive (backups)

## Key Components

1. **VYNTRA Solaris v5.0** - Main reference for any AI agent working on this SaaS
2. **Astro v5** - Static Site Generator with Tailwind CSS
3. **FastAPI backend** - Python backend with Supabase PostgreSQL
4. **GSAP animations** - Scrollytelling experience on landing page
5. **Authentication flow** - JWT Bearer header + httpOnly cookie
6. **Design system** - "Solar Technocratic" with maroon + gold color scheme

## Implementation Plan

### Phase 1: Quick Wins (Frontend)
- Fix E8: Add .jpeg to file upload accept
- Fix M10: Replace inline styles with Tailwind classes
- Fix M2: Add user-facing error feedback
- Fix M8: Remove mode: 'no-cors' from health check

### Phase 2: Backend Critical Fixes
- Fix E9: Remove bson import from academic.py
- Fix E10: Grade filter in students router
- Fix E14: Password reset delivery
- Fix E17: Guardrail bypass

### Phase 3: Backend Maintenance
- Fix E11: Grade mapping in admin router
- Fix E12: Mock request in grades router
- Fix E13: Propagation note count
- Fix E15: E2E test credentials
- Fix E16: ABP detection
- Fix E18: grade_badge_class

### Phase 4: Structural Improvements
- M11-M21 improvements for quality and security

## Verification Checklist
- Build frontend: `npm run build`
- Run backend tests: `cd backend && python3 -m pytest tests/ -v`
- No remaining patterns: onclick=, AbortSignal.timeout, __import__, mode: 'no-cors', bson