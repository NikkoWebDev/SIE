# Comprehensive Fixes — Implementation Plan
**Goal:** Resolve all active bugs (E8-E18) and maintenance items (M1-M21) across frontend and backend  
**Architecture:** Frontend Astro v5 pages use BaseLayout + DashboardShell pattern with Tailwind CSS; backend is FastAPI on Supabase (PostgreSQL). Fixes must preserve build integrity (`npm run build`) and pass existing tests.  
**Tech Stack:** Astro v5, Tailwind CSS v3, Chart.js, FastAPI, Supabase (PostgreSQL), pytest, Playwright

---

## Phase 1: Frontend Quick Fixes (Low Effort, High Impact)

### Step 1.1 — E8: Add `.jpeg` to file upload accept

**File:** `src/pages/estudiante.astro:126`

Replace:
```
accept=".pdf,.doc,.docx,.zip,.png,.jpg"
```
With:
```
accept=".pdf,.doc,.docx,.zip,.png,.jpg,.jpeg"
```

**Verify:** `rg "accept=" src/pages/estudiante.astro` shows `.jpeg` present.

---

### Step 1.2 — M10: Replace inline `style="display:none"` with Tailwind classes

**File:** `src/layouts/Layout.astro:72`

Replace `<svg style="display:none">` with `<svg class="hidden">`:
```diff
- <svg id="theme-icon-moon" class="h-5 w-5" fill="none" ... style="display:none">
+ <svg id="theme-icon-moon" class="h-5 w-5 hidden" fill="none" ...>
```
And the sun icon `class="hidden dark:block"` pattern:
```diff
- <svg id="theme-icon-sun" class="h-5 w-5" fill="none" ...>
+ <svg id="theme-icon-sun" class="h-5 w-5 hidden dark:block" fill="none" ...>
```
Then remove the inline JS that toggles `style.display` and use `classList.toggle('hidden')` instead (or rely on the dark: class).

**Verify:** `npm run build` succeeds. Toggle theme still shows/hides correct icon.

---

### Step 1.3 — M2: Add user-facing error feedback for silent catches

**Files:** `src/pages/estudiante.astro` (lines 329, 425, 475, 527, 541)

For each `.catch(function(){})`, replace with:
```js
.catch(function(err) {
  window.VyntraToast?.error("Error al cargar datos. Intenta de nuevo.");
  console.error("[loadX] Error:", err);
})
```

Functions affected: `loadWelcomeData`, `loadExams`, `loadSchedule`, `loadLibrary`, `loadCandidates`.

**Verify:** Trigger a network failure in devtools → toast appears.

---

### Step 1.4 — M8: Remove `mode: 'no-cors'` from health check

**File:** `src/pages/login.astro:218`

Replace:
```js
fetch(baseUrl + '/api/health', { method: 'GET', mode: 'no-cors' })
```
With:
```js
fetch(baseUrl + '/api/health', { method: 'GET' })
```

Add a `.then` to set a visual indicator:
```js
.then(r => { if (r.ok) showServerStatus('connected'); })
.catch(() => showServerStatus('disconnected'));
```

**Verify:** Health check response is readable in network tab.

---

### Step 1.5 — Build + verify Phase 1

```bash
npm run build
```

Expected: 7 pages compiled, no errors.

---

## Phase 2: Frontend Structural Improvements

### Step 2.1 — M1: Migrate `onclick` HTML attributes to `addEventListener`

**Files affected:** `docente.astro:253`, `admin.astro:135`, `estudiante.astro:543`, and any other `onclick="..."` in HTML.

**Pattern:**
1. Add `id` or `data-js` attribute to elements with `onclick`
2. Move handler logic to a `<script>` block with `addEventListener`
3. Remove the `onclick` attribute from HTML

Example refactor:
```diff
- <button onclick="showSection('notas')">Notas</button>
+ <button data-section="notas" class="js-section-btn">Notas</button>
```
Script:
```js
document.querySelectorAll('.js-section-btn').forEach(btn => {
  btn.addEventListener('click', () => showSection(btn.dataset.section));
});
```

**Verify:** All navigation buttons still work. `rg "onclick=" src/pages/` shows zero matches.

---

### Step 2.2 — M6: Add inline form validation

**Files:** `src/pages/login.astro`, `src/pages/admin.astro`, `src/pages/docente.astro`

Add `oninput`/`onblur` validation for:
- Email/credential format
- Password minimum length (6 chars)
- Required fields

Strategy: Create a small `validateField(field, rules)` utility in an inline script or shared lib that:
1. Shows inline error text below the field
2. Adds error styling (red border)
3. Clears error on valid input

**Example for login:**
```js
document.getElementById('credential').addEventListener('blur', function() {
  if (this.value.trim().length < 3) {
    showFieldError(this, 'Ingresa un usuario o email válido');
  } else {
    clearFieldError(this);
  }
});
```

**Verify:** Tab through form fields → inline errors appear/clear correctly.

---

### Step 2.3 — M3: Fix Chart.js race condition

**Files:** `DashboardShell.astro:46-48`, `estudiante.astro:393`, `admin.astro:278`

Replace `setTimeout` retry pattern with a proper promise/deferred pattern:

In `DashboardShell.astro`:
```js
window.__ChartReady = Chart;
// dispatch event for consumers
window.dispatchEvent(new CustomEvent('chart:ready', { detail: Chart }));
```

In consumer pages:
```js
function getChart() {
  return new Promise(resolve => {
    if (window.__ChartReady) return resolve(window.__ChartReady);
    window.addEventListener('chart:ready', e => resolve(e.detail), { once: true });
  });
}

// Usage
getChart().then(Chart => { /* init chart */ });
```

This eliminates all `setTimeout` retries.

**Verify:** Charts render on first load without console errors. Remove `setTimeout` calls.

---

### Step 2.4 — M9: Lazy load dashboard sections

**File:** `src/pages/estudiante.astro`

Currently all 9 sections are in HTML with `display:none`. Replace with a pattern that only renders section content when activated:

```js
const sectionLoaders = {
  inicio: () => import('./sections/inicio.js'),
  notas: () => import('./sections/notas.js'),
  // ...
};

function showSection(id) {
  if (!loadedSections.has(id)) {
    loadedSections.add(id);
    sectionLoaders[id]().then(module => module.render(document.getElementById(`section-${id}`)));
  }
  // show/hide logic...
}
```

For a lighter approach: move API calls for each section from `DOMContentLoaded` to the section's `showSection` call.

**Verify:** Network tab shows API calls only when section is first opened.

---

### Step 2.5 — M7: Add `AbortSignal.timeout()` polyfill or replace

**Files:** `index.astro:220,228`, `BaseLayout.astro:107`

Option A: Replace with `setTimeout` + `AbortController`:
```js
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5000);
fetch(url, { signal: controller.signal }).finally(() => clearTimeout(timeout));
```

Option B: Create a polyfill:
```js
if (!AbortSignal.timeout) {
  AbortSignal.timeout = ms => {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), ms);
    return ctrl.signal;
  };
}
```

Prefer Option A for clarity.

**Verify:** `rg "AbortSignal.timeout" src/` shows zero occurrences.

---

### Step 2.6 — M5: Remove service worker unregister

**File:** `BaseLayout.astro:95`

If no PWA is planned, keep the unregister but wrap in a check:
```js
// Comment explaining why: prevent stale service workers from legacy deployment
navigator.serviceWorker?.getRegistrations().then(registrations => {
  registrations.forEach(r => r.unregister());
});
```

Or remove entirely if there's no legacy concern.

Decision: Keep but add comment + optional `?.` chaining.

**Verify:** `rg "serviceWorker" src/layouts/BaseLayout.astro` shows the cleaned-up version.

---

### Step 2.7 — M4: Auth state consistency

**File:** `src/lib/auth.ts`

Add a `/api/auth/verify` call on page load to check if the httpOnly cookie is still valid:

```js
async function verifyAuth() {
  try {
    const res = await window.vfetch('/api/auth/verify');
    if (!res.ok) throw new Error('Session expired');
    return true;
  } catch {
    // Clear localStorage + redirect to login
    localStorage.removeItem('userId');
    localStorage.removeItem('userRole');
    localStorage.removeItem('userName');
    window.location.href = '/login';
    return false;
  }
}
```

Call `verifyAuth()` in `BaseLayout` on page load. If it fails, redirect before rendering dashboard.

**Verify:** Delete httpOnly cookie in devtools → refresh → redirect to login. Clear localStorage only → stays logged in.

---

### Step 2.8 — Build + verify Phase 2

```bash
npm run build
```

---

## Phase 3: Backend Critical Fixes

### Step 3.1 — E9: Remove `bson` import from `academic.py`

**File:** `backend/models/academic.py`

1. Remove `from bson import ObjectId`
2. Replace `ObjectId` usage with `uuid` (PostgreSQL native UUID type)
3. If file is completely unused (all models exist in `schemas.py`), add deprecation notice and remove imports

**Decision:** The models in `academic.py` (`GradeDB`, `SubjectDB`, `DeliveryDB`, `GuideDB`) may be duplicates of `schemas.py`. Check imports across backend to see if anything imports from `academic.py`. If not used, delete or mark as `_legacy_academic.py`.

```bash
rg "from.*models.*academic" backend/ --include "*.py"
```

**Verify:** `python3 -c "from backend.models import academic"` does not crash.

---

### Step 3.2 — E10: Fix grade filter in students router

**File:** `backend/routers/students.py:29`

Current (broken):
```python
query = query.eq("grade", grade)
```

Fix: query through `student_metadata → course` relationship:
```python
# Get course IDs matching the grade name
course_ids = supabase.table("courses").select("id").eq("name", grade).execute()
if course_ids.data:
    ids = [c["id"] for c in course_ids.data]
    query = query.in_("course_id", ids)
```

**Verify:** `GET /api/students?grade=10-A` returns students in that course.

---

### Step 3.3 — E14: Fix password reset delivery

**File:** `backend/routers/password_reset.py`

Add actual delivery mechanism. Options:
- If email is configured (SMTP/SendGrid), send email
- If SMS is configured (Twilio), send SMS
- Otherwise, log the code with a clear console message for dev environments

Minimal fix:
```python
# Try email delivery
try:
    send_reset_email(data.login_credential, code)
    logger.info("Reset code sent to %s", data.login_credential)
except Exception as e:
    logger.warning("Email not configured. Reset code for %s: %s", data.login_credential, code)
```

**Verify:** Request password reset → code appears in logs or gets delivered.

---

### Step 3.4 — E17: Fix guardrail bypass

**File:** `backend/routers/guardrails.py:64`

Return a well-defined sentinel instead of `None`:
```python
class GuardResult:
    OK = "OK"
    BLOCKED = "BLOCKED"

def check_input(text: str) -> str:
    if injection_detected:
        return GuardResult.BLOCKED
    return GuardResult.OK
```

Update caller in `ai_agent.py`:
```python
from .guardrails import GuardResult
guard_result = check_input(user_message)
if guard_result == GuardResult.BLOCKED:
    return {"error": "Mensaje bloqueado por seguridad."}
```

**Verify:** Send injection prompt → blocked message returned. Send normal prompt → passes through.

---

### Step 3.5 — Run backend tests

```bash
cd backend && python3 -m pytest tests/ -v
```

---

## Phase 4: Backend Maintenance

### Step 4.1 — E11: Fix `grado` mapping in admin router

**File:** `backend/routers/admin.py:371-372`

Replace `current_status` with actual course name:
```python
# Get course name from student_metadata → courses
course_id = meta_map.get(p["id"], {}).get("course_id")
course_name = "Sin asignar"
if course_id:
    course = supabase.table("courses").select("name").eq("id", course_id).execute()
    if course.data:
        course_name = course.data[0]["name"]
"grado": course_name,
"grade": course_name,
```

**Verify:** Admin panel shows course name (e.g. "10-A") instead of "AL_DIA".

---

### Step 4.2 — E12: Fix mock request in grades router

**File:** `backend/routers/grades.py:122-123`

Replace `type()` mock with a proper Request-like object or refactor `financial_guard` to accept `student_id` directly:

Option A: Refactor `financial_guard` to accept `student_id` as parameter (preferred).
Option B: Create a proper mock:
```python
from starlette.requests import Request
class MockRequest:
    def __init__(self, student_id):
        self.query_params = {"student_id": student_id}
        self.method = "GET"
        self.headers = {}
```

**Verify:** Grade submission with financial guard enabled works without errors.

---

### Step 4.3 — E13: Fix propagation note count

**File:** `backend/routers/teachers.py:171`

```diff
- propagation_note = f"Nota propagada automáticamente a las {len(propagated) + 1} materias vinculadas"
+ propagation_note = f"Nota propagada automáticamente a las {len(propagated)} materias vinculadas"
```

**Verify:** When `propagated = []`, note says "0 materias vinculadas".

---

### Step 4.4 — E15: Fix E2E test credentials

**File:** `tests/vyntra.e2e.spec.js`

Update credentials to match `seed.sql`:
```javascript
await loginAs(page, 'student', '101', 'alumno');
await loginAs(page, 'teacher', '11', 'profe');
await loginAs(page, 'admin', '1', 'admin');
```

Or update `seed.sql` to match test expectations (if tests reflect real desired state).

Also update `loginAs` helper if needed.

**Verify:** `npm run test` passes against a freshly seeded database.

---

### Step 4.5 — E16: Fix ABP detection

**File:** `backend/routers/teachers.py:170`

Replace keyword-based detection with DB column lookup:
```python
is_abp = subject_data.get("is_abp", False)
```

Fetch `is_abp` from `subjects` table instead of checking keywords in name.

**Verify:** Subject "Matemáticas Recreativas" is NOT marked as ABP unless `is_abp = true` in DB.

---

### Step 4.6 — E18: Fix `grade_badge_class` or remove from backend

**File:** `backend/models/schemas.py:236`

Two options:
1. Remove the field (frontend can determine styling)
2. Return standard CSS class names that exist in Tailwind:
```python
return {
    "excellent": "text-green-600",
    "good": "text-blue-600",
    "failing": "text-red-600",
}.get(status, "text-gray-600")
```

**Verify:** Frontend receives valid Tailwind class names.

---

### Step 4.7 — Build + verify Phase 4

```bash
cd backend && python3 -m pytest tests/ -v
```

---

## Phase 5: Backend Improvements (M11-M21)

### Step 5.1 — M11: Clean up duplicate models

**Files:** `backend/models/academic.py`, `backend/models/schemas.py`

1. Identify unique model definitions in `academic.py` not in `schemas.py`
2. Move any unique ones to `schemas.py`
3. Add deprecation warning to `academic.py`:
```python
import warnings
warnings.warn("academic.py is deprecated. Use schemas.py instead.", DeprecationWarning, stacklevel=2)
```

**Verify:** `rg "from.*models.*academic" backend/` shows zero imports (all migrated).

---

### Step 5.2 — M12: Add Redis-backed rate limiter

**File:** `backend/main.py:76`

Add `slowapi` with Redis backend (or `upstash-redis`):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL"))
```

Or if Redis not available, at least add a comment/TODO documenting the limitation.

---

### Step 5.3 — M13: Add body size limit

**File:** `backend/main.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB

class BodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Request body too large"}, status_code=413)
        return await call_next(request)
```

**Verify:** POST with >10MB body returns 413.

---

### Step 5.4 — M14: Add Alembic migration system

```bash
cd backend && pip install alembic && alembic init alembic
```

Create initial migration from current schema:
```bash
alembic revision --autogenerate -m "initial schema"
```

**Verify:** `alembic history` shows initial migration.

---

### Step 5.5 — M15: Reduce JWT expiry to 4 hours

**File:** `backend/dependencies.py:45`

```diff
- TOKEN_EXPIRY_HOURS: int = int(os.getenv("TOKEN_EXPIRY_HOURS", "8"))
+ TOKEN_EXPIRY_HOURS: int = int(os.getenv("TOKEN_EXPIRY_HOURS", "4"))
```

**Verify:** Token expires after 4h by default.

---

### Step 5.6 — M16: Fix `__import__("asyncio")`

**File:** `backend/routers/ai_agent.py:609,615`

Replace `__import__("asyncio").sleep(...)` with `asyncio.sleep(...)`

**Verify:** `rg "__import__" backend/` shows zero matches.

---

### Step 5.7 — M17: Fix SQL injection risk

**File:** `backend/routers/ai_agent.py:473` and `backend/seed.sql:66`

Use parameterized queries:
```sql
EXECUTE format('SELECT * FROM (%s LIMIT 100) t', query_text)
```
And add `quote_literal` where needed.

---

### Step 5.8 — M18: Add structured auth logging

**File:** `backend/routers/auth.py`

Add logging with structured fields:
```python
logger.warning("failed_login_attempt", extra={
    "ip": request.client.host,
    "credential": masked_credential,
    "timestamp": datetime.utcnow().isoformat(),
})
```

**Verify:** Failed login attempts appear in logs with IP and timestamp.

---

### Step 5.9 — M19: Fix hardcoded CORS origin

**File:** `backend/main.py:146`

```diff
- allow_origins=["https://vyntraacademic.netlify.app"],
+ allow_origins=os.getenv("ALLOWED_ORIGINS", "https://vyntraacademic.netlify.app").split(","),
```

**Verify:** CORS works with `ALLOWED_ORIGINS` env var.

---

### Step 5.10 — M20: Lazy load Chart.js

**File:** `DashboardShell.astro:46-48`

Replace static import with dynamic import:
```js
async function loadChartJS() {
  const { Chart, registerables } = await import('chart.js');
  Chart.register(...registerables);
  window.__ChartReady = Chart;
  window.dispatchEvent(new CustomEvent('chart:ready', { detail: Chart }));
}
// Load on demand when a chart section is shown
```

**Verify:** Chart.js is only loaded when navigating to a section with charts.

---

### Step 5.11 — M21: Fix TEXT→UUID migration fragility

**File:** `backend/migrations/001_schema_optimizer.sql`

Add validation step before conversion:
```sql
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM "public"."notices"
    WHERE "teacher_id" IS NOT NULL AND "teacher_id" !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
    
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % rows with invalid UUIDs in notices.teacher_id', invalid_count;
    END IF;
END $$;
```

**Verify:** Migration fails clearly if data is invalid, rather than silently leaving TEXT columns.

---

### Step 5.12 — Build + verify Phase 5

```bash
cd backend && python3 -m pytest tests/ -v
```

---

## Phase 6: Structural Cleanup (S1-S6)

### Step 6.1 — S1+S2: Deprecate Layout.astro and session.js

**File:** `src/layouts/Layout.astro`

Add deprecation comment at top:
```astro
---
// DEPRECATED: Not used by any active page. BaseLayout.astro is the current root layout.
---
```

**File:** `public/js/session.js`

Add deprecation comment. Optionally, remove if nothing imports it.

**Verify:** `src/layouts/Layout.astro` is not referenced by any Astro page.

---

### Step 6.2 — S3: Update E2E tests to remove non-existent role tabs

**File:** `tests/vyntra.e2e.spec.js`

Remove test steps that click role tabs on login page (they don't exist).

**Verify:** Tests reflect actual login page structure.

---

### Step 6.3 — Update docs

- `docs/bugs.md`: Move resolved items, update statuses
- `AGENTS.md`: Update known issues list
- `C_sol/claude.md`: Cross-reference completed fixes

**Verify:** Grep for outdated references.

---

## Verification Checklist (Final)

```bash
# Frontend
npm run build                    # 7 pages, zero errors
npm run test                     # Playwright E2E passes

# Backend
cd backend && python3 -m pytest tests/ -v  # all tests pass

# No remaining known patterns
rg "onclick=" src/pages/         # zero matches
rg "AbortSignal.timeout" src/    # zero matches
rg "__import__" backend/         # zero matches
rg "mode: 'no-cors'" src/        # zero matches
rg "bson" backend/               # zero matches (or only in deprecation comments)
rg "from.*models.*academic" backend/ --include "*.py"  # zero matches
```

---

## Effort Summary

| Phase | Items | Est. Time | Impact |
|-------|-------|-----------|--------|
| 1. Frontend Quick Fixes | E8, M2, M8, M10 | ~30 min | 🟡 UX fixes |
| 2. Frontend Structural | M1, M3-M7, M9 | ~3 h | 🟠 Maintainability |
| 3. Backend Critical | E9, E10, E14, E17 | ~2 h | 🔴 Stability |
| 4. Backend Maintenance | E11-E13, E15-E16, E18 | ~2 h | 🟠 Correctness |
| 5. Backend Improvements | M11-M21 | ~4 h | 🟢 Quality |
| 6. Structural Cleanup | S1-S3, docs | ~1 h | 🟢 Hygiene |
| **Total** | **30+ items** | **~12.5 h** | |

## Ordering Rationale

Phases are ordered by confidence-to-effort ratio:
- **Phase 1**: Max confidence, minimal effort — immediate UX wins
- **Phase 2**: Higher effort but clears all frontend technical debt
- **Phase 3**: Critical backend bugs that block functionality
- **Phase 4+5**: Backend correctness and quality — can be deferred if time is tight
- **Phase 6**: Non-functional cleanup — lowest priority
