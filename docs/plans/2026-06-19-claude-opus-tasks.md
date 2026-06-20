# Tareas para Claude Opus 4.8 — VYNTRA Solaris

> Contexto optimizado: docs limpios, bugs críticos resueltos, código base estable.
> Build: OK (7 páginas, 0 errores). Backend: FastAPI + Supabase. Frontend: Astro v5 SSG.
> QA E2E: 143 tests, 143 pass (2026-06-20). Suite en `tests/comprehensive-qa.spec.js`.

---

## OP-1: Instalar CORSMiddleware correctamente

**Archivo:** `Vyntra/backend/main.py`
**Severidad:** 🔴 Crítico

**Problema:** `CORSMiddleware` está importado (línea 23) pero NUNCA se instala. En su lugar, CORS se maneja manualmente en 5 middlewares distintos (`csrf_middleware`, `rate_limit_middleware`, `security_headers_middleware`, `auth_middleware`, `financial_guard_middleware`) y en los exception handlers mediante la función `_get_cors_origin()` y headers `Access-Control-*` manuales.

Esto causa:
- Preflight `OPTIONS` no se maneja correctamente (falta `Access-Control-Request-Method` y `Access-Control-Request-Headers`)
- `Access-Control-Expose-Headers` no se setea nunca
- Cualquier nuevo middleware debe recordar agregar CORS manualmente
- Riesgo de headers inconsistentes entre middlewares

**Tarea:**
1. Agregar `app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])` junto a los otros middlewares (línea ~160)
2. Simplificar/eliminar los headers CORS manuales de los middlewares
3. Mantener `_get_cors_origin()` para los exception handlers (que sí necesitan CORS porque están fuera del middleware stack normal)
4. Verificar que `OPTIONS` preflight sigue funcionando en `security_headers_middleware`

**Líneas clave:** 23, 107-154, 160, 188, 207, 225, 243, 268

---

## OP-2: Sanitizar consumo de body en financial_guard_middleware

**Archivo:** `Vyntra/backend/main.py:266-296`
**Severidad:** 🔴 Crítico

**Problema:** `financial_guard_middleware` hace `body = await request.body()` en línea 272, lo que CONSUME el stream del body. Cualquier route handler downstream que necesite parsear el body (ej: Pydantic models via POST/PUT) recibe un body vacío.

```python
# Línea 272 — ESTO ROMPE EL BODY PARA HANDLERS DOWNSTREAM
body = await request.body()
```

**Tarea:** Refactorizar para extraer `student_id` sin consumir el body. Opciones:
- **(A) Dependency de FastAPI:** Crear un `Depends(financial_guard)` que se ejecute antes del parsing de parámetros y rechace antes de que FastAPI intente parsear el body. Esto es lo más limpio.
- **(B) Cachear el body:** Leer `await request.body()` una vez, cachearlo en `request._body`, y usar `request.body()` en vez de `await request.body()` en handlers. Patrón estándar de Starlette.
- **(C) Restringir a query params:** Solo validar `student_id` de `request.query_params` para GET y confiar en path params para POST/PUT.

**Recomendación:** Opción A (dependency) es la más idiomática en FastAPI.

**Líneas clave:** 266-296, `dependencies.py` (financial_guard actual)

---

## OP-3: Optimizar N+1 queries en ABP grade propagation

**Archivo:** `Vyntra/backend/routers/teachers.py:99-123`
**Severidad:** 🟠 Alta

**Problema:** La función `_propagate_abp_grade` hace 2 queries DB por cada materia objetivo ABP:
```python
for target_name in ABP_PROPAGATED_SUBJECTS:  # 9 materias
    # Query 1: buscar subject por nombre
    target_subj = db.table("subjects").select("id").eq("name", target_name).execute()
    # Query 2: verificar si ya existe grade
    existing = db.table("grades").select("*").eq("student_id", student_uuid).eq("subject_id", target_subj_id).execute()
```
Con 9 materias en `ABP_PROPAGATED_SUBJECTS` → **18 round-trips a la DB**.

**Tarea:**
1. Batch-load: un solo query `.in_("name", ABP_PROPAGATED_SUBJECTS)` para obtener todos los subject_ids
2. Batch-check: un solo query `.in_("subject_id", subject_ids)` para verificar existing grades
3. Procesar en memoria qué materias necesitan insert vs update

---

## OP-4: Reemplazar agregación Python-side con DB aggregates en admin_stats

**Archivo:** `Vyntra/backend/routers/admin.py:38-67`
**Severidad:** 🟠 Alta

**Problema:** `admin_stats` fetchea TODAS las filas de `student_metadata` (línea 46) y `grades` (línea 55) para contar/calcular en Python:
```python
# Fetch ALL rows — para 1000 estudiantes = 10K+ filas transferidas
meta = db.table("student_metadata").select("*").execute()
mora_count = sum(1 for m in (meta.data or []) if m.get("months_in_arrears", 0) >= 2)

grades = db.table("grades").select("score").execute()
avg_score = sum(g["score"] for g in (grades.data or [])) / len(grades.data or [1])
```

**Tarea:**
1. Reemplazar `mora_count` con: `db.table("student_metadata").select("*", count="exact").gte("months_in_arrears", 2).execute()` 
2. Para average: si Supabase no soporta `avg()` nativamente, al menos limitar con `.select("score").limit(1000)` o usar RPC
3. Bonus: reemplazar `total_teachers = (total_teachers or 0) + (total_admins or 0)` en línea 62 — es un bug semántico que infla el conteo de docentes

---

## OP-5: Activar `section-router.ts` y eliminar duplicación en 3 dashboards

**Archivos:**
- `Vyntra/src/lib/section-router.ts` (87 líneas, implementado pero NUNCA usado)
- `Vyntra/src/pages/estudiante.astro:288-314`
- `Vyntra/src/pages/docente.astro:171-192`  
- `Vyntra/src/pages/admin.astro:155-177`

**Problema:** `showSection()`, `staggerCards()`, y los maps `sectionTitles`/`sectionSubs` están triplicados (~130 líneas de lógica idéntica) en los 3 dashboards. `section-router.ts` fue escrito específicamente para reemplazar esto pero ningún dashboard lo importa.

**Tarea:**
1. Importar `section-router.ts` en los 3 dashboards (ya se importa via `<script>` en `BaseLayout.astro:233`)
2. Reemplazar las funciones `showSection()` y `staggerCards()` inline con llamadas a `window.__sectionRouter.showSection(id)` (o como esté expuesto)
3. Verificar que:
   - La navegación entre secciones funciona en los 3 roles
   - El `CustomEvent('vyntra:navigate')` se sigue disparando (para sync del sidebar)
   - Los títulos y subtítulos del Topbar se actualizan correctamente
   - `content-visibility: auto` se aplica/remueve correctamente (agregado recientemente)
4. Si `section-router.ts` necesita ajustes para cubrir los 3 dashboards, hacerlos

---

## Verificación final

```bash
cd Vyntra && npm run build        # Debe: 7 páginas, 0 errores
cd Vyntra/backend && .venv/bin/python -m pytest tests/ -v --tb=short  # Debe: 32+ pass
```

---

## Notas

- El código usa `var` (no `let`/`const`), funciones anónimas (`function(){}`), y patrones ES5 en los dashboards. Mantener el estilo existente.
- Los archivos `.astro` mezclan HTML + JS inline en `<script>` blocks. No extraer a archivos externos a menos que sea necesario.
- La documentación canónica está en `C_sol/claude.md`. No duplicar.
- El Supabase URL es `https://fpombaziyombczyfdryt.supabase.co`
