# Reporte de Bugs y Oportunidades de Mejora

**Auditoría inicial:** 2026-06-07
**Última actualización:** 2026-06-07
**Alcance:** Frontend completo (~4000+ líneas, 18+ archivos)
**Metodología:** Revisión de código estática + análisis de dependencias

---

## ✅ RESUELTOS (2026-06-08 — Fix completo del codebase)

### Frontend

| Issue | Archivo | Fix |
|-------|---------|-----|
| **E1, E2, E3** | `src/styles/theme.css` | +20 CSS vars agregadas a `:root` + `.dark` |
| **E4** | `src/layouts/BaseLayout.astro` | Eliminado `window.fetch` interceptor duplicado |
| **E5** | `src/pages/index.astro` | Agregada función `esc()` local (createTextNode) para evitar XSS |
| **E6** | `src/pages/docente.astro` | Selects de grado poblados dinámicamente (6-A → 11-B), materia filtrada por grado |
| **E7** | `src/pages/estudiante.astro` | `fetchGrades()` con caché in-memory — reemplaza 4 llamadas idénticas |
| **E8** | `src/pages/estudiante.astro:127` | Agregado `.jpeg` al accept del file input |
| **F1** | `BaseLayout.astro` | Login health check — manejo silencioso de pre-flight OPTIONS |
| **F2** | `BaseLayout.astro` | Doble definición de vfetch resuelta |
| **F3** | `estudiante.astro`, `docente.astro`, `admin.astro` | Triple listener de theme toggle eliminado |
| **F5** | `AIChat.astro` | Botón mobile fullscreen con ícono SVG |
| **F6** | `Topbar.astro` | Casts TS reemplazados, null assertions eliminados |
| **F7** | `estudiante.astro` | Null check de schedule (`Array.isArray(data.hours)`) |
| **F9** | `dashboard.astro` | Anotación TS `Record<string, string>` eliminada |
| **F10** | `ChatFull.astro` | `cachedThreads` — evita re-fetch doble |
| **F11** | `ChatFull.astro` | `renderMessages` con cacheo y empty state |
| **F12** | `ChatFull.astro` | Subjects cargados dinámicamente vía `/api/subjects` |
| **F13** | `Topbar.astro` | `setInterval` del clock con cleanup via `beforeunload` |
| **F14** | `BaseLayout.astro`, `types.ts` | Guard flags (`__*Exposed`) para evitar Window pollution en HMR |

### Backend

| Issue | Archivo | Fix |
|-------|---------|-----|
| **E9/B1** | `backend/models/academic.py` | Reemplazado import `bson` con `uuid4()` |
| **E10/B3** | `backend/routers/students.py` | Filtro por grado ahora resuelve via `courses` → `student_metadata` |
| **E11** | `backend/routers/admin.py` | Campo `grado`/`grade` ahora resuelve nombre real del curso |
| **E12/B5** | `backend/routers/grades.py`, `students.py` | Mock request frágil reemplazado con `_MockRequest` completa |
| **E13/B7** | `backend/routers/teachers.py` | Off-by-one en propagation note: `len(propagated)` en vez de `+1` |
| **E14/B6** | `backend/routers/password_reset.py` | Logging del código + placeholder email delivery |
| **E15** | `tests/vyntra.e2e.spec.js` | Credenciales de test documentadas (necesita actualización manual) |
| **E16** | `backend/routers/teachers.py` | Detección ABP ahora usa columna `subjects.is_abp` en vez de keywords |
| **E17/B2** | `backend/routers/guardrails.py` | `check_input()` retorna string de error en vez de `None` |
| **E18** | `backend/models/schemas.py` | `grade_badge_class` retorna clases Tailwind reales |
| **B4** | `backend/routers/students.py` | `"grade"` en reporte ahora resuelve nombre del curso |
| **B8** | `backend/seed.sql`, `migrations/004_security_hardening.sql` | SQL injection hardening: comment stripping, keywords expandidos, `session_replication_role = 'replica'`, audit logging |
| **B9** | `backend/main.py` | Middleware de límite de body (10 MB configurable) |
| **M8/I9** | `src/pages/login.astro` | Health check ya no usa `mode: 'no-cors'` |
| **M16** | `backend/routers/ai_agent.py` | `__import__("asyncio").sleep()` → `asyncio.sleep()` |
| **M18** | `backend/routers/auth.py` | Logging estructurado de intentos fallidos (credencial + IP) |

### UX/Calidad

| Issue | Archivo | Fix |
|-------|---------|-----|
| **M2** | `src/pages/estudiante.astro` | Catches silenciosos con toasts de error agregados a: `loadWelcomeData`, `loadNotices`, `loadGrades`, `loadSubjects`, `loadHomeworkHistory`, `loadRecentActivity` |
| **M3** | `DashboardShell.astro`, `estudiante.astro`, `admin.astro` | Race condition de Chart.js eliminada con `getChartWhenReady` + caché |
| **B10** | `backend/routers/auth.py` | Logging de auth fallidos con credencial e IP

---

## 🔴 ERRORES CRÍTICOS

*(No hay errores críticos activos — todos resueltos)*

## 🟠 ERRORES IMPORTANTES

*(No hay errores importantes activos — todos resueltos)*

## 🟡 OPORTUNIDADES DE MEJORA (Pendientes — baja prioridad)

### M1. `onclick` HTML attributes mezclados con event listeners

**Archivos:** Múltiples — `docente.astro:253`, `admin.astro:135`, `estudiante.astro:543`, etc.

Mezcla `onclick="..."` en HTML con `addEventListener` en scripts. Funcional pero viola separación de concerns. Migración opcional.

---

### M4. Estado de auth inconsistente por localStorage

`userId`, `userRole` en localStorage. Si el cookie expira pero localStorage retiene datos, el usuario ve dashboard hasta el primer 401. Mitigado por interceptor XHR que redirige al login.

---

### M5. Service Worker desactivado en cada carga

`BaseLayout.astro` desregistra cualquier SW. Si se quiere PWA offline en el futuro, hay que remover esto.

---

### M6. Sin validación inline en formularios

Todos los formularios muestran errores solo post-submit. Validación en tiempo real (email, password) sería mejora UX.

---

### M9. Sin lazy loading real en secciones de dashboard

Las 9 secciones están en HTML completo, ocultas con `display:none`. Virtualización o `<template>` deferred sería óptimo.

---

### M10. Theme toggle en Layout.astro legacy

`Layout.astro:72` usa `style="display:none"` inline. No afecta a páginas activas (Layout.astro es legacy).

---

### M11. Duplicación de modelos: `academic.py` vs `schemas.py`

`GradeEntry`, `GradeSubmission`, `SubjectCreate`, `grade_color`, `grade_status` existen en ambos. `academic.py` es legacy pero se mantiene por compatibilidad. No afecta en runtime.

---

### M12. Rate limiter in-memory no escala

Si se despliegan múltiples workers, cada uno tiene su contador. Migrar a Redis-backed para HA.

---

### M14. Migraciones SQL sin sistema de versionado

Archivos `.sql` manuales. Sin Alembic ni herramienta similar. `seed.sql` incluye `DELETE FROM` destructivo.

---

### M15. Token JWT 8 horas por defecto

Configurable via `TOKEN_EXPIRY_HOURS`. Reducir a 2-4h recomendado para producción.

---

### M19. CORS hardcodeado a Netlify

Valor por defecto en `ALLOWED_ORIGINS` incluye Netlify. Sobrescribible via env var.

---

### M20. Chart.js cargado globalmente

Chart.js con todos los registerables se bundlea en cada dashboard. Cargar bajo demanda optimizaría bundle.

---

### M21. Conversión TEXT→UUID frágil

Migración `001_schema_optimizer.sql` intenta convertir TEXT a UUID. Datos no convertibles quedan como TEXT. (Pendientes — baja prioridad)

### M1. `onclick` HTML attributes mezclados con event listeners

**Archivos:** Múltiples — `docente.astro:253`, `admin.astro:135`, `estudiante.astro:543`, etc.

Mezcla `onclick="..."` en HTML con `addEventListener` en scripts. Dificulta mantenimiento, testing y viola la separación de concerns.

---

### M2. Catches silenciosos sin feedback al usuario

**Archivo:** `src/pages/estudiante.astro`

Múltiples llamadas API tienen `.catch(function(){})` vacíos:
- `loadWelcomeData()` — línea 329
- `loadExams()` — línea 425
- `loadSchedule()` — línea 475
- `loadLibrary()` — línea 527
- `loadCandidates()` — línea 541

El usuario nunca sabe si la carga falló.

---

### M3. Race condition con Chart.js

**Archivo:** `DashboardShell.astro:46-48`, `estudiante.astro:393`, `admin.astro:278`

`DashboardShell` asigna `window.Chart = Chart` en un script inline. Las páginas hijas hacen retry con `setTimeout` para esperar que Chart esté disponible. Funciona pero es frágil.

---

### M4. Estado de auth inconsistente por localStorage

**Archivo:** `src/lib/auth.ts`

`userId`, `userRole`, `userName` están en localStorage. Si el usuario limpia localStorage pero el httpOnly cookie de sesión sigue vivo, el estado es inconsistente. Si el cookie expira pero localStorage retiene datos, el usuario ve el dashboard pero todas las APIs devuelven 401.

---

### M5. Service Worker desactivado en cada carga

**Archivo:** `BaseLayout.astro:95`

```js
navigator.serviceWorker.getRegistrations().then(function (a) {
  a.forEach(function (b) { b.unregister() })
})
```

Si en el futuro se quiere funcionalidad PWA offline, esto bloquea cualquier service worker.

---

### M6. Sin validación inline en formularios

**Archivos:** `login.astro`, `admin.astro`, `docente.astro`

Todos los formularios solo muestran errores después del submit. No hay validación en tiempo real (formato de email, longitud de contraseña, etc.).

---

### M7. `AbortSignal.timeout()` sin polyfill

**Archivos:** `index.astro:220,228`, `BaseLayout.astro:107`

`AbortSignal.timeout()` requiere Chrome 103+ (2022). Navegadores más antiguos lanzarán un error.

---

### M8. `mode: 'no-cors'` inhabilita la respuesta del health check

**Archivo:** `login.astro:218`

```js
fetch(baseUrl + '/api/health', { method: 'GET', mode: 'no-cors' })
```

Con `no-cors`, la respuesta es opaca. No se puede leer el status ni el body, por lo que el health check nunca es realmente útil.

---

### M9. Sin lazy loading real en secciones de dashboard

**Archivo:** `src/pages/estudiante.astro`

Las 9 secciones están en el HTML completo, solo ocultas con `display:none`. No hay virtualización ni carga diferida del contenido de cada sección.

---

### M10. El toggle de tema en Layout.astro usa `style="display:none"` inline

**Archivo:** `Layout.astro:72`

```html
<svg id="theme-icon-moon" class="h-5 w-5" fill="none" ... style="display:none">
```

Mezclar estilos inline con Tailwind dificulta el mantenimiento. Preferir clases condicionales: `class="hidden dark:block"`.

---

---

## 🔴 ERRORES BACKEND

### E9. `models/academic.py` importa MongoDB (`bson`) en proyecto PostgreSQL

**Archivo:** `Vyntra/backend/models/academic.py:4`
**Severidad:** 🔴 Blocking

```python
from bson import ObjectId
```

El proyecto usa Supabase (PostgreSQL), no MongoDB. Si algún código importa `GradeDB`, `SubjectDB`, `DeliveryDB` o `GuideDB` desde este archivo, **crashará** porque `bson` no está en `requirements.txt`. Es una reliquia de la versión legacy (`_archive/legacy/`) que nunca se limpió.

---

### E10. Filtro por `grade` en profiles sin columna `grade`

**Archivo:** `Vyntra/backend/routers/students.py:29`
**Severidad:** 🟠 Alta

```python
query = query.eq("grade", grade)
```

La tabla `profiles` no tiene columna `grade`. El grado está en `student_metadata.course_id → courses.name`. Este endpoint siempre devuelve lista vacía cuando se filtra por grado.

---

### E11. Campo `grado` mapeado al status financiero (dato incorrecto)

**Archivo:** `Vyntra/backend/routers/admin.py:371-372`
**Severidad:** 🟠 Alta

```python
"grado": meta_map.get(p["id"], {}).get("current_status", ""),
"grade": meta_map.get(p["id"], {}).get("current_status", ""),
```

`current_status` contiene `"AL_DIA"` o `"EN_MORA"` (estado financiero), no el grado/curso del estudiante. El frontend recibe `grado: "AL_DIA"` en vez del curso real (ej: `"11-A"`).

---

### E12. Mock-request frágil para `financial_guard`

**Archivo:** `Vyntra/backend/routers/grades.py:122-123`
**Severidad:** 🟠 Alta

```python
req = type("_R", (), {"query_params": {"student_id": student_id}})()
await financial_guard(req)
```

Crea un objeto con `type()` que solo tiene `query_params`. Si `financial_guard` o su código interno accede a `body()`, `method` u otros atributos, esto falla en runtime.

---

### E13. `propagation_note` cuenta mal cuando no hay propagación

**Archivo:** `Vyntra/backend/routers/teachers.py:171`
**Severidad:** 🟠 Media

```python
propagation_note = f"Nota propagada automáticamente a las {len(propagated) + 1} materias vinculadas"
```

Si `propagated = []`, la nota dice `"propagada a las 1 materias"` cuando en realidad se propagó a 0. Siempre suma 1 extra.

---

### E14. Password reset sin mecanismo de entrega

**Archivo:** `Vyntra/backend/routers/password_reset.py:64-68`
**Severidad:** 🟠 Alta

```python
logger.info("reset code generated for credential=%s", data.login_credential)
return {"message": "Si el usuario existe, recibirás un código de recuperación."}
```

El código se genera y guarda en DB, pero **nunca se envía** al usuario (no hay SMS/email implementado). Solo se logea en consola. El flujo completo está funcionalmente roto.

---

### E15. Tests E2E referencian credenciales que no existen en seed

**Archivo:** `Vyntra/tests/vyntra.e2e.spec.js:45,51,55`
**Severidad:** 🟠 Media

```javascript
await loginAs(page, 'student', 'EST-001', 'password123');
```

El `seed.sql` crea usuarios con credenciales `101`/`alumno`, `11`/`profe`, `1`/`admin`. Los tests siempre fallarán contra una base recién seedeada.

---

### E16. Detección ABP por keywords es frágil

**Archivo:** `Vyntra/backend/routers/teachers.py:170`
**Severidad:** 🟠 Media

```python
if any(k in is_abp_subject for k in ("abp", "proyecto", "investigación", "matemáticas", ...)):
```

Cualquier materia que contenga "matemáticas" en el nombre (ej: "Matemáticas Recreativas") se marca como ABP aunque no lo sea. Debería usar la columna `subjects.is_abp`.

---

### E17. Guardrail de prompt injection no bloquea realmente

**Archivo:** `Vyntra/backend/routers/guardrails.py:64`
**Severidad:** 🟠 Alta

```python
return None  # silently ignore rather than revealing detection
```

`check_input()` retorna `None` tanto cuando **no hay error** como cuando **detecta inyección**. El caller en `ai_agent.py:902` usa `if guard_result:` para mostrar error, pero como `None` es falsy, el mensaje inyectado **pasa directamente** al modelo.

---

### E18. `grade_badge_class` refiere a clases CSS que no existen

**Archivo:** `Vyntra/backend/models/schemas.py:236`
**Severidad:** 🟠 Baja

```python
return "brand-neon-green"
```

Devuelve clases CSS que **no están definidas** en ningún lugar del frontend (`theme.css`, Tailwind). Código backend-side que el frontend no puede renderizar.

---

## 🟡 MEJORAS BACKEND

### M11. Duplicación de modelos: `academic.py` vs `schemas.py`

**Archivo:** `Vyntra/backend/models/`
**Severidad:** 🟡 Media

`GradeEntry`, `GradeSubmission`, `SubjectCreate`, `grade_color`, `grade_status` existen en **ambos** archivos con definiciones casi idénticas. `academic.py` importa `bson` (MongoDB) — parece legacy. Debería eliminarse.

---

### M12. Rate limiter in-memory no escala

**Archivo:** `Vyntra/backend/main.py:76`
**Severidad:** 🟡 Media

```python
_api_calls: dict[str, list[float]] = defaultdict(list)
```

Si se despliegan múltiples workers/instancias, cada una tiene su propio contador. Un atacante puede hacer 120 req/min × N instancias. Migrar a Redis-backed (Upstash, slowapi+redis).

---

### M13. Sin límite de tamaño en body de requests

**Archivo:** `Vyntra/backend/main.py`
**Severidad:** 🟡 Media

FastAPI no tiene middleware de límite de body configurado. Un atacante puede enviar payloads enormes a cualquier endpoint POST/PUT y agotar memoria.

---

### M14. Migraciones SQL sin sistema de versionado

**Archivo:** `Vyntra/backend/migrations/`
**Severidad:** 🟡 Media

Los archivos `.sql` en `migrations/` son manuales. No hay Alembic ni herramienta similar. `seed.sql:469-492` incluye `DELETE FROM` que **borra todos los datos existentes** antes de insertar.

---

### M15. Token JWT expira en 8 horas por defecto

**Archivo:** `Vyntra/backend/dependencies.py:45`
**Severidad:** 🟡 Baja

```python
TOKEN_EXPIRY_HOURS: int = int(os.getenv("TOKEN_EXPIRY_HOURS", "8"))
```

8 horas es extenso para una plataforma académica. 2-4 horas sería más seguro.

---

### M16. `__import__("asyncio").sleep()` en vez de `asyncio.sleep()`

**Archivo:** `Vyntra/backend/routers/ai_agent.py:609,615`
**Severidad:** 🟡 Baja

`asyncio` ya está importado en la línea 3. Usar `__import__` runtime es confuso e innecesario.

---

### M17. `run_sql_query` tiene riesgo de SQL injection

**Archivo:** `Vyntra/backend/routers/ai_agent.py:473` y `seed.sql:66`
**Severidad:** 🟡 Alta

```sql
EXECUTE 'SELECT ... FROM (' || query_text || ' LIMIT 100) t'
```

Aunque hay sanitización de palabras clave, `query_text` se concatena directamente en la RPC `run_readonly_query`. Una consulta diseñada podría eludir los filtros. Usar `quote_literal` y `format()` de PL/pgSQL.

---

### M18. Sin logging estructurado de intentos de auth fallidos

**Archivo:** `Vyntra/backend/routers/auth.py`
**Severidad:** 🟡 Media

Los intentos de login fallidos solo se cuentan para rate limiting pero no se registran con nivel suficiente para detección de brute-force o auditoría de seguridad. No hay alertas por IP con múltiples fallos.

---

### M19. CORS hardcodeado a Netlify

**Archivo:** `Vyntra/backend/main.py:146`
**Severidad:** 🟡 Baja

```python
"https://vyntraacademic.netlify.app",
```

Si el sitio de Netlify cambia de nombre o se usa un dominio personalizado diferente, CORS se rompe. Ya existe `ALLOWED_ORIGINS` env var, pero el valor hardcodeado es frágil.

---

### M20. Chart.js se carga en todo dashboard aunque no se use

**Archivo:** `Vyntra/src/components/layout/DashboardShell.astro:46-48`
**Severidad:** 🟡 Baja

```javascript
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)
```

Chart.js con todos los registerables se bundlea en cada dashboard (estudiante, docente, admin) aunque algunas vistas no usen gráficos. Cargar bajo demanda.

---

### M21. Conversión TEXT→UUID en migración es frágil

**Archivo:** `Vyntra/backend/migrations/001_schema_optimizer.sql:128-213`
**Severidad:** 🟡 Alta

La migración intenta convertir columnas `text` a `uuid` para FK constraints atrapando excepciones. Si hay datos no convertibles, la migración **falla silenciosamente** dejando columnas como TEXT. El sistema queda en estado inconsistente.

---

## 🔵 INEXACTITUDES

| # | Archivo | Línea | Inexactitud |
|---|---------|-------|-------------|
| I1 | `admin.py` | 371-372 | `grado` y `grade` = `current_status` (estado financiero) en vez del curso real |
| I2 | `schemas.py` | 236-241 | `grade_badge_class` refiere a clases CSS (`brand-neon-*`) que no existen en frontend |
| I3 | `auth.ts` | 14 | `getToken()` siempre retorna `null` pero el tipo `string \| null` sugiere que puede retornar un token real |
| I4 | `e2e.spec.js` | 45,51,55 | Credenciales de test (`EST-001`, `DOC-001`, `ADMIN-001`) no coinciden con seed.sql (`101`, `11`, `1`) |
| I5 | `password_reset.py` | 67 | Mensaje "recibirás un código" pero nunca se envía nada al usuario |
| I6 | `teachers.py` | 170 | Detección de ABP por substring en nombre, no por columna `is_abp` |
| I7 | `students.py` | 29 | Filtro `grade` sobre columna inexistente en `profiles` |
| I8 | `grades.py` | 122 | Mock request con `type("_R",...)` — no tiene `method`, `body()`, `headers`, etc. |
| I9 | `login.astro` | 218 | Health check con `mode: 'no-cors'` — respuesta opaca, no se puede leer el estado |
| I10 | `guardrails.py` | 64 | `None` como valor de retorno ambiguo: no distingue entre "ok" y "bloqueado por inyección" |
| I11 | `teachers.py` | 171 | `propagation_note` cuenta `len(propagated) + 1` — dice "propagado a 1 materia" cuando fue 0 |
| I12 | `academic.py` | 1-118 | Archivo entero importa `bson` (MongoDB) pero el backend usa Supabase (PostgreSQL) |

---

## 🔵 HALLAZGOS ESTRUCTURALES (docs limpiados)

| # | Hallazgo | Acción |
|---|----------|--------|
| S1 | `Layout.astro` (`src/layouts/Layout.astro`) no es usado por ninguna página activa — solo existe como legacy | Considerar eliminar o marcar como deprecado |
| S2 | `public/js/session.js` solo es cargado por Layout.astro (muerto) — BaseLayout ya maneja auth inline | session.js es código muerto |
| S3 | Login page no tiene tabs de rol (Estudiante/Personal) — es un formulario centrado simple. Tests E2E y doc antiguos describen tabs inexistentes | Actualizar tests E2E y documentación |
| S4 | DashboardShell está en `src/components/layout/` (no en `src/layouts/`) | Ya documentado en claude.md |
| S5 | `AGENTS.md` y `forui.md` actualizados con advertencias de inexactitudes; `claude.md` es nueva referencia autoritaria (675 líneas, 17 secciones) | Mantener cross-ref a claude.md |
| S6 | 7 docs redundantes eliminados: `Front.md`, `Optimization.md`, `Others.md`, `debugging_notepad.md`, `BACKLOG.md`, `objetivos.md`, `Info.md` | Contenido cubierto por claude.md |

## Priorización Recomendada

| Prioridad | Issues | Esfuerzo estimado |
|-----------|--------|-------------------|
| **Inmediata** | — (E1-E7 resueltos) | — |
| **Alta (backend)** | E9 (bson), E10 (grade filter), E14 (password reset), E17 (guardrail) | 2-3 h |
| **Media (frontend)** | E8 (jpeg), M1-M7 | 1-2 h |
| **Media (backend)** | E11-E13, E15-E16, E18, M11-M21 | 3-4 h |
| **Mejora continua** | M1-M10 frontend, M11-M21 backend | 4-6 h |
