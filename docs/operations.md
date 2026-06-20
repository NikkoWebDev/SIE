# Operations — Vyntra Solaris v5.0

> Fecha: 2026-06-19 — Consolidado de Optimization.md + Others.md

---

## Deploy

- **Frontend:** Netlify (`https://vyntraacademic.netlify.app`) — static SSG
- **Backend:** Render (`https://sie-8agt.onrender.com`) — FastAPI
- **Canonical:** `https://colegiociudaddelsol.edu.co`
- **Config:** `netlify.toml` (redirects, CSP, cache). `vercel.json` archivado.

## Cold start (Render free tier)

El backend se suspende tras ~15 min sin tráfico. Primer request tras inactividad: 30-60s.
- `BaseLayout.astro` hace ping a `/api/health` en cada carga
- Recomendado: cron-job.org o UptimeRobot cada 10 min

## Rate limiter

In-memory (120 req/60s por IP). No escala a multi-worker. Documentado en `main.py`.
TODO: Redis-backed (Upstash, slowapi) para HA.

## Cache de assets

`netlify.toml` no tiene cabeceras de caché para `/assets/*`. Recomendado:
```toml
[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

## Seguridad

- **CSP:** Definido en `BaseLayout.astro` (no en netlify.toml)
- **CSRF:** Double Submit Cookie implementado
- **CORS:** Configurado para Netlify + localhost. `ALLOWED_ORIGINS` env var para dominios adicionales.
- **Google Service Account Key:** Rotar si fue comprometida (estaba en `_secrets/`, ya en `.gitignore`)
- **Google OAuth Client ID:** Via `PUBLIC_GOOGLE_CLIENT_ID` env var

## APIs verificadas (última verificación v5.0.3)

| Endpoint | Estado |
|----------|--------|
| `/api/health` | ✅ 200 |
| `/api/auth/login` | ✅ 200 |
| `/api/admin/stats` | ✅ 200 |
| `/api/admin/students` | ✅ 200 |
| `/api/students/risk` | ✅ 200 |
| `/api/grades?student_id=X` | ✅ 200 |
| `/api/subjects` | ✅ 200 |
| `/api/notices` | ✅ 200 |
| `/api/ai/student-tutor` | ✅ SSE streaming |
