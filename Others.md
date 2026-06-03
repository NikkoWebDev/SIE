# Others — Vyntra Academic v5.0

> Fecha: 2026-06-03
> Hallazgos misceláneos: backend, seguridad, testing, documentación, deploy, git

---

## 1. SEGURIDAD — BLOQUEANTE — Migración a httpOnly cookies INCOMPLETA (auth roto)

**Hallazgo:** El frontend inició la migración a httpOnly cookies pero está a medias:

| Componente | Estado | Evidencia |
|------------|--------|-----------|
| `login.astro` | ✅ No almacena `access_token` en localStorage | 0 ocurrencias de `access_token` en localStorage.setItem |
| `src/lib/auth.ts` | ✅ `getToken()` retorna null, usa `credentials: 'include'` | Línea 14 |
| `src/lib/api.ts` | ✅ `apiFetch()` usa `credentials: 'include'` + CSRF | Línea 15 |
| Dashboards (estudiante/admin/docente) | ❌ Siguen leyendo `localStorage.getItem('access_token')` | Líneas 234/145/156 respectivamente |
| `public/js/dashboard.js` | ❌ `vfetch()` lee `access_token` de localStorage | Línea 42 |
| Backend login endpoint | ❌ No establece httpOnly cookie (sin Set-Cookie header) | Verificado con curl |
| Backend `dependencies.py` | ⚠️ Soporta cookies httpOnly pero no activas | Código existe, no implementado |

**Impacto:** El sistema de autenticación está ROTO. Login → dashboard → 401 → login (loop infinito). El usuario no puede usar ninguna funcionalidad protegida.

**Verificación en vivo:**
- Login API retorna `access_token` en JSON (funciona)
- Backend NO envía `Set-Cookie` header
- Login guarda metadata (userRole, userName, userId, profile_id, userGrade) en localStorage
- Login NO guarda `access_token` en localStorage
- Dashboard `vfetch()` envía `Authorization: Bearer null` → 401 → redirect a /login

**Recomendación:**
- Opción A (inmediata): Restaurar `localStorage.setItem('access_token', data.access_token)` en `login.astro`
- Opción B (correcta): Completar la migración:
  1. Backend: implementar `Set-Cookie` httpOnly JWT en `/api/auth/login`
  2. Backend: implementar endpoint CSRF token
  3. Frontend: dashboards usar `apiFetch()` de `lib/api.ts` en lugar de `vfetch()` inline
  4. Frontend: remover lectura de `access_token` en dashboards y `dashboard.js`

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

## 4. SEGURIDAD — BAJO — Sin CSP (Content Security Policy)

**Hallazgo:** No hay header `Content-Security-Policy` en `netlify.toml`. Los headers existentes son:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 0`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

**Recomendación:**
- Agregar CSP para restringir orígenes de scripts (los CDN de Chart.js, jsPDF, etc.).
- Ejemplo:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://apis.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://sie-8agt.onrender.com https://vyntra-backend.onrender.com;
  ```

---

## 5. SEGURIDAD — BAJO — Sin CSRF protection

**Hallazgo:** Las rutas del backend no implementan tokens CSRF. Las cookies httpOnly JWT (si se implementan) serían vulnerables a CSRF.

**Recomendación:**
- Si se migra a cookies httpOnly, implementar `SameSite=Strict` (ya soportado en `dependencies.py` para producción).
- Para operaciones mutantes (POST, PUT, DELETE), validar un header `X-CSRF-Token`.

---

## 6. BACKEND — ALTO — Backend inconsistente (tres URLs)

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
- ✅ `vercel.json` archivado como `vercel.json.archived`
- Unificar a UNA URL canónica: `sie-8agt.onrender.com`
- Eliminar referencias a `vyntra-backend.onrender.com` y `backend-colegio-hdx7.onrender.com`

---

## 7. BACKEND — MEDIO — AI Tutor funcional pero sin persistencia

**Hallazgo:** El AI Tutor VYNTRA funciona correctamente:
- ✅ Endpoint `POST /api/ai/student-tutor?user_id=X` responde con SSE streaming
- ✅ Respuesta coherente: "¡Hola! Con gusto te ayudo con matemáticas..."
- El historial usa `OrderedDict` en memoria (se pierde al reiniciar)

**Migración:** Existe `backend/migrations/004_chat_history.sql` (agregado en v5.0.2) para persistencia. `backend/routers/ai_search.py` también fue agregado.

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

**Hallazgo:** Hay 7 archivos de test/script en `tests/`:
- `vyntra.e2e.spec.js` — parece incompleto o placeholder
- `vyntra-ui-improvements.spec.js` — nuevo, pocas pruebas
- `audit.spec.cjs`, `debug_admin.cjs`, `debug_admin2.cjs`, `debug_estudiante.cjs` — scripts de depuración, no tests reales
- `monitor.mjs` — script de monitoreo

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

## 12. DEPLOY — BAJO — ✅ Resuelto: Config Netlify unificada

**Estado:** En v5.0.2:
- `vercel.json` archivado como `vercel.json.archived`
- `netlify.toml` es la única configuración activa
- El sitio está deployado en Netlify: `https://vyntraacademic.netlify.app`
- `AGENTS.md` aún menciona "Vercel (static + serverless)" — necesita actualización

**Verificación en vivo:**
- Deploy en Netlify funcional
- URLs con hash de Astro para assets
- Tema "Solaris" desplegado correctamente

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

| Categoría | Prioridad | Issue |
|-----------|-----------|-------|
| **Auth** | 🔴 BLOQUEANTE | Migración httpOnly cookie incompleta — auth roto (login→dashboard→login loop) |
| **Seguridad** | 🔴 Alto | Rotar Google Service Account Key (comprometida) |
| **Backend** | 🟡 Medio | AI Tutor sin persistencia (migración `004_chat_history.sql` existe) |
| **Backend** | 🟢 Bajo | `/api/teachers` retorna 404 (debe ser `/api/admin/teachers`) |
| **Testing** | 🟡 Medio | Tests E2E incompletos, no ejecutados en CI |
| **Documentación** | 🟢 Bajo | README.md mínimo, AGENTS.md desactualizado |
| **Deploy** | ✅ FIXED | Vercel archivado, solo Netlify activo |
| **Git** | ✅ FIXED | Secrets en .gitignore, imágenes WebP |
| **Frontend** | ✅ FIXED | Bug `{n[0]}` resuelto en v5.0.2 |
| **Frontend** | 🟢 Bajo | Chart.js/jspdf CDN sin SRI |
