# Vyntra Academic — Solaris v5.0

Plataforma educativa del **Colegio Técnico Ciudad del Sol** (Sogamoso, Boyacá, Colombia).
Gestión académica, financiera, tutoría IA y comunicación escolar.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | **Astro v5** (SSG) + Tailwind CSS v3 |
| Backend | **FastAPI** (Python) |
| Base de datos | **Supabase** (PostgreSQL) |
| Auth | JWT en cookies httpOnly + CSRF |
| AI | OpenRouter API (tutoría por roles) |
| Deploy | Netlify (frontend) + Render (backend) |

## Setup local

```bash
# 1. Variables de entorno
cp .env.example .env       # Backend
cp .env .env.local         # Frontend (Astro)
# Editar .env con tus credenciales

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload  # http://localhost:8000

# 3. Frontend
cd ..
npm install
npm run dev                # http://localhost:4321
```

## Variables de entorno

| Variable | Dónde se usa | Requerida |
|----------|-------------|-----------|
| `JWT_SECRET` | Backend (HS256) | ✅ |
| `SUPABASE_URL` | Backend (DB) | ✅ |
| `SUPABASE_SERVICE_KEY` | Backend (service role) | ✅ |
| `SUPABASE_ANON_KEY` | Backend (anónimo) | ✅ |
| `PUBLIC_API_URL` | Frontend + Netlify build | ✅ |
| `OPENROUTER_STUDENT_KEY` | AI Tutor (estudiantes) | Para AI |
| `OPENROUTER_TEACHER_KEY` | AI Tutor (docentes) | Para AI |
| `OPENROUTER_ADMIN_KEY` | AI Tutor (administrativos) | Para AI |
| `GOOGLE_CLIENT_ID` | Google OAuth | Para OAuth |
| `PUBLIC_GOOGLE_CLIENT_ID` | Frontend (Netlify UI) | Para OAuth |
| `SENTRY_DSN` | Backend (monitoreo) | Opcional |

## Comandos útiles

```bash
npm run dev           # Frontend: servidor de desarrollo
npm run build         # Frontend: build estático
npm run check         # Type-checking (astro check)
npm run test          # E2E tests (headless CI)
npm run test:ui       # E2E tests (con navegador visible)
npm run test:backend  # Backend tests (pytest)
```

## Tests

```bash
# Frontend E2E (Playwright)
npm run test          # Headless (CI)
npm run test:ui       # Con Chromium visible

# Backend (pytest)
cd backend
pip install -r tests/requirements-test.txt
pytest tests/ -v --cov=.
```

## Migraciones

Las migraciones SQL están en `backend/migrations/`. Ejecutar en orden en Supabase Dashboard:

1. `001_schema_optimizer.sql`
2. `002_password_reset.sql`
3. `003_security_hardening.sql`
4. `004_chat_history.sql`

O, para instalación limpia: ejecutar `backend/seed.sql` completo.

## Deploy

- **Frontend**: Netlify (build automático desde `main`, `npm run build`)
- **Backend**: Render (FastAPI, `uvicorn main:app`)
- **CI**: GitHub Actions (lint → test backend → test frontend → build → deploy)

## Enlaces

- Frontend: https://vyntraacademic.netlify.app
- Backend API: https://sie-8agt.onrender.com/api/health
