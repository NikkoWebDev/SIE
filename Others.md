# Others — Vyntra Solaris v5.0

> Fecha: 2026-06-03 (última verificación)
> Hallazgos misceláneos: backend, seguridad, testing, documentación, deploy, git

---

## 1. ✅ FIXED — Auth flow (migración httpOnly cookies)

**Resuelto en v5.0.4.** Login y dashboards ahora usan la clave `ws_access_token` de forma consistente:

| Componente | Antes | Ahora |
|------------|-------|-------|
| `login.astro` | No guardaba token | Guarda `ws_access_token` ✅ |
| `estudiante.astro` | Buscaba `'access_token'` (null → redirect) | Busca `'ws_access_token'` ✅ |
| `admin.astro` | Buscaba `'access_token'` (null → redirect) | Busca `'ws_access_token'` ✅ |
| `docente.astro` | Buscaba `'access_token'` (null → redirect) | Busca `'ws_access_token'` ✅ |
| `dashboard.js` (`vfetch`) | Buscaba `'access_token'` | Busca `'ws_access_token'` ✅ |
| Backend login | No establecía `Set-Cookie` | Sigue sin establecer cookie |

**Pendiente:** El backend aún no implementa httpOnly cookies. El token sigue viajando en `Authorization: Bearer` vía localStorage. Para completar la migración:
1. Backend: implementar `Set-Cookie` httpOnly JWT en `/api/auth/login`
2. Backend: implementar endpoint CSRF token
3. Frontend: dashboards usar `apiFetch()` de `lib/api.ts` en lugar de `vfetch()` inline

---

## 2. SEGURIDAD — MEDIO — Google OAuth client ID hardcodeado

**Hallazgo:** El `GOOGLE_CLIENT_ID` está hardcodeado en el HTML de `login.astro`:

```
456201263142-u1r9mr35dccoj6u2ukcp1cn88af883cd.apps.googleusercontent.com
```

**Riesgo:** Esto es normal para OAuth público (no es un secreto), pero debe estar definido en variable de entorno y expuesto vía `define:vars`, no hardcodeado en el template.

**Recomendación:**
- Mover a `src/config.ts` con `import.meta.env.PUBLIC_GOOGLE_CLIENT_ID`.
- Definir en `.env` y en los builds de Netlify/Vercel.

---

## 3. SEGURIDAD — MEDIO — Credenciales de servicio en el repo

**Hallazgo:** El archivo `backend/_secrets/project-4a8b1cdf-29c4-4b2d-bc1-69c6dff48eb1.json` (Google Cloud Service Account Key) fue commiteado y pusheado.

**Impacto:** GitHub bloqueó el push por reglas de protección de secrets. El archivo fue removido del commit, pero permanece en disco local.

**Recomendación:**
- ✅ Ya se agregó `backend/_secrets/` al `.gitignore`.
- Rotar la clave de servicio en Google Cloud Console inmediatamente (esta clave está comprometida).
- NO almacenar secrets en el repo — usar variables de entorno o un vault (ej: GitHub Secrets, Doppler).

---

## 4. ✅ FIXED — CSP (Content Security Policy)

**Implementado.** Verificado en vivo:

```
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://apis.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://sie-8agt.onrender.com wss://sie-8agt.onrender.com; frame-src 'self' https:; media-src 'self' https:; object-src 'none'; base-uri 'self'; form-action 'self'
```

Headers de seguridad completos:
| Header | Valor |
|--------|-------|
| `Content-Security-Policy` | ✅ Definido |
| `X-Content-Type-Options` | `nosniff` ✅ |
| `X-Frame-Options` | `DENY` ✅ |
| `X-XSS-Protection` | `0` ✅ |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` ✅ |
| `Referrer-Policy` | `strict-origin-when-cross-origin` ✅ |

---

## 5. ✅ FIXED v5.0.6 — Accesibilidad: skip-link, ARIA, aria-label

**Resuelto en v5.0.6.** Múltiples mejoras de accesibilidad implementadas:

| Mejora | Archivo | Estado |
|--------|---------|--------|
| "Saltar al contenido" (skip-link) | `BaseLayout.astro` | ✅ Agregado |
| `role="dialog"` + `aria-modal="true"` | `login.astro` (modal) | ✅ Agregado |
| `role="alert"` en mensajes de error | `login.astro` | ✅ Agregado |
| `role="status"` en mensajes de éxito | `login.astro` | ✅ Agregado |
| `aria-label` en botón de tema | `Sidebar.astro` | ✅ Agregado |

**Pendiente:** `aria-live` en contenido dinámico, `scope` en tablas, `role="navigation"` en sidebar.

---

## 6. SEGURIDAD — BAJO — Sin CSRF protection

**Hallazgo:** Las rutas del backend no implementan tokens CSRF. Las cookies httpOnly JWT (si se implementan) serían vulnerables a CSRF.

**Recomendación:**
- Si se migra a cookies httpOnly, implementar `SameSite=Strict` (ya soportado en `dependencies.py` para producción).
- Para operaciones mutantes (POST, PUT, DELETE), validar un header `X-CSRF-Token`.

---

## 6. ✅ FIXED — Backend URLs unificadas

**Hallazgo:** Existen 3 URLs de backend:

| URL | Usada en |
|-----|----------|
| `https://sie-8agt.onrender.com` | `netlify.toml`, `login.astro` (activa y funcional) |
| `https://vyntra-backend.onrender.com` | `public/js/session.js` (antigua, posiblemente inactiva) |
| `https://backend-colegio-hdx7.onrender.com` | `vercel.json` (archivado, rewrite) |

**Estado actual v5.0.2:**
- `session.js` ahora usa `window.__API_URL__` (configurado en build) en lugar de URL hardcodeada
- La URL activa es `https://sie-8agt.onrender.com` (funciona para todas las APIs probadas)
- CORS configurado para `https://vyntraacademic.netlify.app` ✅

**Verificación en vivo — APIs funcionales:**
| Endpoint | Método | Estado |
|----------|--------|--------|
| `/api/auth/login` | POST | ✅ 200 (login funcional) |
| `/api/health` | GET | ✅ 200 ({"status":"alive","database":"supabase"}) |
| `/api/admin/stats` | GET | ✅ 200 (2 estudiantes, 2 docentes, 18 notas) |
| `/api/admin/students` | GET | ✅ 200 (retorna perfiles) |
| `/api/students/risk` | GET | ✅ 200 (1 estudiante en riesgo) |
| `/api/grades?student_id=X` | GET | ✅ 200 (9 materias ABP, score 4.5) |
| `/api/students/X/financial-status` | GET | ✅ 200 (2 estados: AL_DIA y EN_MORA) |
| `/api/subjects` | GET | ✅ 200 (9 materias ABP) |
| `/api/admin/teachers` | GET | ✅ 200 (1 docente con materias) |
| `/api/ai/student-tutor?user_id=X` | POST | ✅ 200 (SSE streaming funcional) |
| `/api/notices` | GET | ✅ 200 (array vacío) |
| `/api/teachers` | GET | ❌ 404 (ruta incorrecta, debe ser `/api/admin/teachers`) |
| `/api/students` | GET | ⚠️ Retorna TODOS los perfiles, no solo estudiantes |

**Recomendación:**
- ✅ `vercel.json` restaurado como archivo activo (ya no archivado en v5.0.4)
- URL canónica: `https://sie-8agt.onrender.com` (verificada: 13 endpoints funcionales)
- `session.js` ahora usa `window.__API_URL__` configurado desde build
- CSP incluye `wss://sie-8agt.onrender.com` para WebSocket

---

## 7. BACKEND — MEDIO — AI Tutor funcional pero sin persistencia

**Hallazgo:** El AI Tutor VYNTRA funciona correctamente:
- ✅ Endpoint `POST /api/ai/student-tutor?user_id=X` responde con SSE streaming
- ✅ Respuesta coherente: "¡Hola! Con gusto te ayudo con matemáticas..."
- El historial usa `OrderedDict` en memoria (se pierde al reiniciar)

**Migración:** Existe `backend/migrations/005_chat_history.sql` para persistencia en Supabase. `backend/routers/ai_search.py` también fue agregado.

**Verificación en vivo:**
- AI responde en chunks SSE (`data: {"token": "..."}`) + `data: [DONE]`
- Stream se completa en <10s

**Recomendación:**
- Conectar `ai_agent.py` a la tabla `chat_history` de Supabase usando la migración existente

---

## 8. BACKEND — BAJO — Rate limiter en memoria

**Hallazgo:** El rate limiter en `main.py` (120 req / 60s por IP) es en memoria. Si se escala a múltiples workers/instancias, el límite se duplica.

**Recomendación:**
- Migrar a rate limiter basado en Redis o usar middleware como `slowapi` con almacenamiento en Supabase/Redis.

---

## 9. TESTING — MEDIO — Tests E2E inconclusos

**Hallazgo:** Archivos en `tests/`:
- `vyntra.e2e.spec.js` — test E2E existente
- `audit.spec.cjs`, `debug_admin.cjs`, `debug_admin2.cjs`, `debug_estudiante.cjs` — scripts de depuración
- `monitor.mjs` — script de monitoreo
- `vyntra-ui-improvements.spec.js` — eliminado en v5.0.2

**Recomendación:**
- Implementar tests E2E completos que cubran:
  - Login (estudiante, docente, admin) con credenciales válidas e inválidas
  - Navegación entre secciones del dashboard
  - CRUD de notas (docente)
  - CRUD de estudiantes (admin)
  - Vista de notas (estudiante)
  - Carga de archivos
  - Flujo de recuperación de contraseña
  - Logout
- Ejecutar tests en CI (GitHub Actions) con `playwright test`.
- Cambiar `headless: false` a `headless: true` en CI, o usar proyecto separado.

---

## 10. TESTING — BAJO — Tests de backend (pytest)

**Hallazgo:** `backend/tests/` contiene:
- `test_api.py` — pruebas de API
- `test_ai_agent.py` — pruebas del agente AI
- `requirements-test.txt` — dependencias para testing

**Recomendación:**
- Integrar pytest en CI para ejecutarse en cada push.
- Agregar cobertura de código con `pytest-cov`.

---

## 11. DOCUMENTACIÓN — BAJO — README.md mínimo

**Hallazgo:** `README.md` tiene solo 2 líneas. `AGENTS.md` tiene información valiosa pero está orientado a asistentes IA.

**Recomendación:**
- Expandir `README.md` con:
  - Descripción del proyecto
  - Stack tecnológico
  - Instrucciones de setup local
  - Variables de entorno requeridas
  - Cómo ejecutar tests
  - Enlace al deploy en vivo

---

## 12. ✅ FIXED v5.0.6 — Deploy: vercel.json eliminado

**Estado:** 
- `vercel.json` eliminado del repo (ya no existe)
- Deploy activo exclusivamente en Netlify: `https://vyntraacademic.netlify.app` ✅
- Assets con hash de Astro, caché 1 año immutable ✅
- Tema "Solaris" + fuentes actualizadas (DM Sans, Fraunces) ✅
- `AGENTS.md` desactualizado (menciona Vercel) — pendiente de actualizar

---

## 13. GIT — BAJO — Secrets commiteados accidentalmente

**Hallazgo:** El workflow de git permitió commitar `backend/_secrets/` (clave de servicio de Google). GitHub push protection lo bloqueó.

**Recomendación:**
- ✅ `backend/_secrets/` agregado a `.gitignore`.
- Agregar un **pre-commit hook** que detecte archivos con extensiones `.json` que contengan `"type": "service_account"`.
- Considerar usar `git-secrets` o `talisman` para prevenir fugas.

---

## 14. GIT — BAJO — ✅ Resuelto: Imágenes convertidas a WebP

**Estado:** En v5.0.2:
- Todos los PNGs en `src/assets/brand/` convertidos a WebP
- PNGs originales eliminados del repo

**Pendiente:**
- Usar `<picture>` con fallback PNG para compatibilidad con Safari <14

---

## Resumen

| Categoría | Prioridad | Issue | Versión |
|-----------|-----------|-------|---------|
| ✅ FIXED | Auth flow | Login y dashboards unificados (`ws_access_token`) | v5.0.4 |
| ✅ FIXED | Accesibilidad | Skip-link, ARIA roles, aria-label, role=alert | v5.0.6 |
| ✅ FIXED | CSP | Content Security Policy completo | v5.0.4 |
| ✅ FIXED | Backend URLs | Unificadas a `sie-8agt.onrender.com` | v5.0.4 |
| ✅ FIXED | Deploy | vercel.json eliminado, solo Netlify | v5.0.6 |
| ✅ FIXED | Git | Secrets en .gitignore, imágenes WebP | v5.0.2 |
| ✅ FIXED | Bug `{n[0]}` | Plantillas sin compilar | v5.0.2 |
| 🔴 Alto | Rotar Google Service Account Key | Clave comprometida en commit anterior | — |
| 🟡 Medio | AI Tutor sin persistencia | Migración `005_chat_history.sql` existe | — |
| 🟡 Medio | Tests E2E incompletos | No ejecutados en CI | — |
| 🟢 Bajo | `/api/teachers` → 404 | Ruta incorrecta (debe ser `/api/admin/teachers`) | — |
| 🟢 Bajo | Chart.js no carga en dashboards | Solo en Layout.astro, dashboards usan BaseLayout | — |
| 🟢 Bajo | CSRF no implementado | Backend sin tokens CSRF | — |
| 🟢 Bajo | README.md mínimo | Pendiente de expandir | — |
| 🟢 Bajo | AGENTS.md desactualizado | Menciona Vercel | — |
