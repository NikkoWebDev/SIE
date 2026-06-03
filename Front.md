# Feedback Frontend — Vyntra Academic v5.0

> Fecha: 2026-06-03
> Sitio en vivo: https://vyntraacademic.netlify.app/
> Repositorio: https://github.com/NikkoWebDev/SIE

---

## 1. ~~BLOQUEANTE~~ ✅ FIXED — Plantillas Astro sin compilar en dashboards

**Estado: RESUELTO en v5.0.2.** El bug `{n[0]}` ya no aparece en producción. Los 3 dashboards tienen navegación hardcodeada funcional. Se validó con 0 ocurrencias en el HTML desplegado.

---

## 2. BLOQUEANTE — Flujo de autenticación roto (migración incompleta a httpOnly cookies)

**Hallazgo:** El login NO almacena `access_token` en localStorage (sigue el nuevo patrón httpOnly cookie), pero los dashboards SÍ lo leen (`var token = localStorage.getItem('access_token')`) y redirigen a `/login` si es null.

**Ciclo:** Login ✅ → Dashboard → `token` es null → redirige a `/login` → Login ✅ → Dashboard → ...

**Causa:** Migración parcial:
- `login.astro`: ✅ Ya no guarda `access_token` en localStorage (solo metadata: userRole, userName, userId, profile_id)
- `estudiante.astro` (línea 234), `admin.astro` (línea 145), `docente.astro` (línea 156), `dashboard.js`: ❌ Siguen leyendo `localStorage.getItem('access_token')` y abortan si es null
- Backend: ❌ No establece httpOnly cookie en login (respuesta sin Set-Cookie header)

**Verificación en vivo:**
- Login API responde con `access_token` en JSON body ✅
- Backend NO envía `Set-Cookie` header ❌
- Login page almacena 5 items en localStorage (userRole, userName, userId, profile_id, userGrade) pero NO access_token
- Dashboard `apiFetch()` y `vfetch()` envían `Authorization: Bearer null` → 401 → redirect loop

**Recomendación:**
- Opción A (rápida): Volver a guardar `access_token` en localStorage desde `login.astro` (revertir parcialmente)
- Opción B (correcta): Implementar httpOnly cookies en el backend + CSRF + actualizar dashboards para NO requerir token en localStorage
- Opción C (híbrida): Dashboard usa `apiFetch()` de `src/lib/api.ts` (que ya usa `credentials: 'include'` + CSRF) en lugar de su propio `vfetch` inline

---

## 3. ALTO — URLs de API inconsistentes

**Hallazgo:** El frontend usa dos URLs de backend distintas:

| Ubicación | URL |
|-----------|-----|
| `public/js/session.js` | `https://vyntra-backend.onrender.com` |
| `login.astro` (inline script) | `https://sie-8agt.onrender.com` |
| `netlify.toml` (env) | `https://sie-8agt.onrender.com` |

**Impacto:** El health check de `session.js` nunca "calienta" el backend real que maneja autenticación. Si las URLs apuntan a servicios distintos, los tokens JWT generados por uno no serán válidos para el otro. Además, la experiencia del primer login sufre cold-start.

**Recomendación:**
- Unificar todas las referencias a una sola URL base.
- Definir `PUBLIC_API_URL` en `.env` y el archivo de deploy, y exponerlo globalmente mediante `define:vars` o `import.meta.env`.
- Eliminar la URL hardcodeada en `session.js` y leerla desde una fuente centralizada.

---

## 3. ALTO — Payload HTML excesivo (todo inline)

**Hallazgo:** Las páginas dashboard contienen todo el CSS (variables de diseño, utilidades) y JS (lógica de negocio, Chart.js setup, CRUD) inline en el HTML:

| Página | Tamaño aproximado |
|--------|-------------------|
| `/estudiante` | ~129 KB |
| `/docente` | ~69 KB |
| `/admin` | ~62 KB |

**Impacto:** Sin caché del navegador para CSS/JS. Cada carga de página descarga todo desde cero. Las métricas Core Web Vitals (LCP, FCP, TBT) se degradan.

**Recomendación:**
- Mover CSS compartido (`theme.css`, Tailwind utilities) a archivos externos (Astro ya lo hace si se importa en el layout).
- Extraer JS de dashboard a módulos `.astro` con `<script>` que Astro procese y genere archivos separados con hash.
- Dividir `estudiante.astro` (~1154 líneas) en componentes más pequeños.

---

## 4. MEDIO — Accesibilidad (ARIA)

**Hallazgo:** Múltiples carencias de accesibilidad detectadas en todas las páginas:

| Issue | Ubicación |
|-------|-----------|
| Sin `role="tab"` / `aria-selected` | Login — selector Estudiante/Personal |
| Sin `role="dialog"` / `aria-modal` | Login — modal de recuperación |
| Sin `aria-live` en contenido dinámico | Dashboards (notas cargadas vía JS, chat) |
| Sin skip-to-content link | Todas las páginas |
| Sin `aria-label` en iconos de navegación | Sidebars, theme toggle |
| Sin `scope="col"` / `scope="row"` en tablas | Planilla de notas, listados de estudiantes |
| Sin `role="navigation"` en sidebars | Todos los dashboards |

**Recomendación:**
- Agregar `role` y `aria-*` a todos los componentes interactivos.
- Implementar un "Saltar al contenido" (skip link).
- Agregar `aria-live="polite"` en áreas que se actualizan dinámicamente (lista de estudiantes, resultados de búsqueda, mensajes del chat).
- Usar `<nav>` semántico para la barra lateral.

---

## 5. MEDIO — Manejo de errores en API

**Hallazgo:** Las páginas dashboard asumen que el backend responde rápido. No hay estados de error visibles ni reintentos:

- Si `fetch` al backend falla, las secciones quedan en "Cargando..." indefinidamente.
- Si el token expira, el usuario es redirigido a `/login` sin mensaje explicativo.
- La página principal (`index.astro`) maneja esto mejor con "--" como fallback.

**Recomendación:**
- Agregar `catch` a todos los `fetch` con un estado de error visible.
- Mostrar un toast o alerta cuando una petición falle.
- Implementar timeout en las peticiones fetch (ej: `AbortController` con 15s).

---

## 6. BAJO — Contraste de color y focus visible

**Hallazgo:**
- El color marrón `#800000` sobre fondo oscuro `#000000` en el sidebar puede tener bajo contraste.
- Los elementos interactivos (links, botones) carecen de un `outline` de foco visible personalizado. Dependen del `outline` por defecto del navegador.

**Recomendación:**
- Agregar `:focus-visible` con un ring de contraste (ej: gold `#FDC003`).
- Verificar ratios de contraste WCAG AA (4.5:1) para todos los textos.

---

## 7. BAJO — UX de carga y retroalimentación

**Hallazgo:**
- El overlay de carga es genérico ("Cargando...") sin indicador de progreso.
- Las transiciones entre secciones del dashboard son instantáneas (sin animación), lo que resulta abrupto.
- El chat del asistente IA no muestra indicador de "escribiendo..." de forma consistente.

**Recomendación:**
- Agregar esqueletos (skeleton screens) por sección en lugar de un spinner global.
- Animar la transición entre secciones con fade o slide suave (CSS transitions).
- Mejorar el feedback del chat con un indicador de typing con animación de puntos.

---

## 8. BAJO — Dependencias CDN sin integridad

**Hallazgo:** Chart.js, jsPDF y autotable se cargan desde CDN sin atributo `integrity`:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js" ...></script>
```

**Impacto:** Vulnerabilidad a ataques de supply chain si el CDN es comprometido.

**Recomendación:**
- Agregar `integrity` con el hash SHA-384 de cada librería.
- Considerar instalar las librerías como dependencias npm y bundlearlas con Astro.

---

## 9. BAJO — Sin favicon en dashboards

**Hallazgo:** Las páginas de dashboard no incluyen el favicon (solo `index.astro` lo tiene). El navegador muestra un icono genérico en la pestaña.

**Recomendación:**
- Agregar el favicon al `<head>` de `Layout.astro` y `BaseLayout.astro`.

---

## 10. BAJO — Título de página descriptivo

**Hallazgo:** Las páginas dashboard tienen títulos como "VYNTRA · Estudiante" sin contexto adicional.

**Recomendación:**
- Incluir el nombre del usuario en el título: "VYNTRA · Panel de Estudiante — Juan Pérez".

---

## Resumen

| Prioridad | Issues |
|-----------|--------|
| **✅ Fixed** | 1. `{n[0]}` resuelto en v5.0.2 |
| **Bloqueante** | 2. Auth flow roto (login ↔ dashboard redirect loop) |
| **Alto** | 3. URLs de API inconsistentes, 4. Payload inline excesivo |
| **Medio** | 5. Accesibilidad ARIA, 6. Manejo de errores API |
| **Bajo** | 7–11. Contraste, UX carga, integridad CDN, favicon, títulos |
