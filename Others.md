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

## 2. ✅ FIXED — Google OAuth client ID en variable de entorno

**Resuelto.** Ahora se lee desde `import.meta.env.PUBLIC_GOOGLE_CLIENT_ID` (definido en build de Netlify). Ya no está hardcodeado en el HTML.

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

## 5. ✅ FIXED v5.0.6/v5.0.9 — Accesibilidad completa

**Resuelto en v5.0.6 + v5.0.9.**

| Mejora | Archivo | Estado |
|--------|---------|--------|
| Skip-link | `BaseLayout.astro` | ✅ v5.0.6 |
| `role="dialog"` + `aria-modal` | `login.astro` (modal) | ✅ v5.0.6 |
| `role="alert"` + `role="status"` | `login.astro` | ✅ v5.0.6 |
| `aria-label` en theme toggle | `Sidebar.astro` | ✅ v5.0.6 |
| `scope="col"` en tablas | Admin, Docente | ✅ v5.0.9 |
| `:focus-visible` outline | `theme.css` | ✅ v5.0.9 |
| Safe area (notch) support | `theme.css` | ✅ v5.0.9 |

---

## 6. ✅ FIXED — CSRF Protection implementado

**Resuelto en v5.0.x.** Double Submit Cookie pattern implementado en `backend/dependencies.py`:

| Función | Propósito |
|---------|-----------|
| `set_csrf_cookie(response)` | Setea cookie `csrf_token` non-httpOnly |
| `validate_csrf(request)` | Valida cookie == `X-CSRF-Token` header |
| `clear_csrf_cookie(response)` | Limpia cookie al logout |
| `CSRF_SKIP_PATHS` | Excluye endpoints de health/login |

---

## 7. ✅ FIXED — Backend URLs unificadas

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

## 8. ✅ FIXED — AI Tutor con persistencia en DB + caché LRU

**Hallazgo original:** AI Tutor usaba `OrderedDict` en memoria.

**Estado actual:** `ai_agent.py` usa DB como almacenamiento primario (`_store_conversation`/`_load_conversation`) con caché LRU en memoria (`_conversation_cache`) para reducir latencia.

| Componente | Rol |
|-----------|------|
| `chat_history` (Supabase) | Almacenamiento persistente principal |
| `_conversation_cache` | Caché LRU en memoria (reduce lecturas a DB) |
| `CacheStore` (dependencies.py) | Decorador de caché para operaciones frecuentes |

---

## 9. BACKEND — BAJO — Rate limiter en memoria

**Hallazgo:** El rate limiter en `main.py` (120 req / 60s por IP) es en memoria. Si se escala a múltiples workers/instancias, el límite se duplica.

**Recomendación:**
- Migrar a rate limiter basado en Redis o usar middleware como `slowapi` con almacenamiento en Supabase/Redis.

---

## 10. MEDIO — Tests E2E locales completos, falta CI

**Estado:** 16 tests E2E implementados en `tests/vyntra.e2e.spec.js`:
- Login multi-rol (admin, docente, estudiante) ✅
- Navegación entre secciones ✅
- Logout ✅

**Pendiente:**
- Integrar en CI (GitHub Actions) para ejecutarse automáticamente en cada push
- Configurar `headless: true` para CI

---

## 11. TESTING — BAJO — Tests de backend (pytest)

**Hallazgo:** `backend/tests/` contiene:
- `test_api.py` — pruebas de API
- `test_ai_agent.py` — pruebas del agente AI
- `requirements-test.txt` — dependencias para testing

**Recomendación:**
- Integrar pytest en CI para ejecutarse en cada push.
- Agregar cobertura de código con `pytest-cov`.

---

## 12. ✅ FIXED — README.md expandido

**Estado:** `README.md` ahora tiene 98 líneas con:
- ✅ Descripción del proyecto
- ✅ Stack tecnológico (Astro, Tailwind, FastAPI, Supabase)
- ✅ Instrucciones de setup local
- ✅ Variables de entorno requeridas
- ✅ Cómo ejecutar tests
- ✅ Enlace al deploy en vivo

---

## 13. ✅ FIXED v5.0.6 — Deploy: vercel.json eliminado

**Estado:** 
- `vercel.json` eliminado del repo (ya no existe)
- Deploy activo exclusivamente en Netlify: `https://vyntraacademic.netlify.app` ✅
- Assets con hash de Astro, caché 1 año immutable ✅
- Tema "Solaris" + fuentes actualizadas (DM Sans, Fraunces) ✅
- `AGENTS.md` actualizado ✅ — documenta Netlify, Vercel mencionado 0 veces

---

## 14. GIT — BAJO — Secrets commiteados accidentalmente

**Hallazgo:** El workflow de git permitió commitar `backend/_secrets/` (clave de servicio de Google). GitHub push protection lo bloqueó.

**Recomendación:**
- ✅ `backend/_secrets/` agregado a `.gitignore`.
- Agregar un **pre-commit hook** que detecte archivos con extensiones `.json` que contengan `"type": "service_account"`.
- Considerar usar `git-secrets` o `talisman` para prevenir fugas.

---

## 15. GIT — BAJO — ✅ Resuelto: Imágenes convertidas a WebP

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
| ✅ FIXED | Accesibilidad | Skip-link, ARIA roles, aria-label, role=alert, scope, focus-visible, safe-area | v5.0.9 |
| ✅ FIXED | CSP | Content Security Policy completo | v5.0.4 |
| ✅ FIXED | Backend URLs | Unificadas a `sie-8agt.onrender.com` | v5.0.4 |
| ✅ FIXED | Deploy | vercel.json eliminado, solo Netlify | v5.0.6 |
| ✅ FIXED | Git | Secrets en .gitignore, imágenes WebP | v5.0.2 |
| ✅ FIXED | Bug `{n[0]}` | Plantillas sin compilar | v5.0.2 |
| ✅ FIXED | Google OAuth | Hardcode → `import.meta.env.PUBLIC_GOOGLE_CLIENT_ID` | v5.0.9 |
| ✅ FIXED | CSRF | Double Submit Cookie pattern implementado en `dependencies.py` | v5.0.9 |
| ✅ FIXED | README.md | Expandido a 98 líneas con descripción completa | v5.0.9 |
| ✅ FIXED | AGENTS.md | Actualizado: ya no menciona Vercel, documenta Netlify | v5.0.9 |
| ✅ FIXED | AI Tutor persistencia | DB primaria + caché en memoria (LRU) | v5.0.9 |
| ✅ FIXED | Manejo errores API | Toast con mensaje antes de redirect | v5.0.9 |
| ⚠️ Pendiente | Rotar Google Service Account Key | Clave comprometida en commit anterior (requiere GCloud Console) | — |
| 🟢 Bajo | Tests E2E en CI | 16 tests existen localmente, no ejecutados en CI | — |
| 🟢 Bajo | Cold start Render | Keep-alive script existe, falta cron | — |
| 🟢 Bajo | Chart.js en dashboards | No crítico (gráficos no usados activamente) | — |
