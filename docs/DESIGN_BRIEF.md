# VYNTRA Solaris — Design Brief v6.0

**Para:** GPT-5.5 (agente de diseño)
**Desde:** Equipo VYNTRA
**Propósito:** Rediseñar la experiencia visual completa del frontend

> ⚠️ **LEE PRIMERO `docs/FRONTEND_COMPLETO.md`** — es la fuente de verdad del estado actual.
> Este brief asume que conoces ese documento. No repite configuración técnica, árbol de archivos, API surface ni bugs resueltos.

---

## RUTAS DEL FRONTEND (MAPA COMPLETO)

```
/                    → src/pages/index.astro       ★ Landing pública (GSAP + 3D Solar Sphere)
/login               → src/pages/login.astro       ★ Login público (BaseLayout)
/dashboard           → src/pages/dashboard.astro   ★ Redirect role-based → /estudiante, /docente, /admin
/estudiante          → src/pages/estudiante.astro  ★ Dashboard estudiante (9 secciones, AIChat, WsRiskAlert)
/docente             → src/pages/docente.astro     ★ Dashboard docente (7 secciones, AIChat)
/admin               → src/pages/admin.astro       ★ Dashboard admin (7 secciones, AIChat, modal CRUD)
/404                 → src/pages/404.astro          ★ Error page (solar eclipse themed)
/api/assets.ts       → (endpoint interno para assets estáticos)
```

Todas las páginas de dashboard usan:
- `BaseLayout.astro` como raíz
- `DashboardShell.astro` como wrapper (Sidebar + Topbar + Toast + LoadingOverlay)
- `AIChat.astro` en las 3 (con role config: student/teacher/admin)
- `WsRiskAlert.astro` solo en estudiante

**Sin router:** Astro SSG genera HTML estático por cada ruta. No hay React Router, no hay SPA.
La navegación entre secciones DENTRO de un dashboard ocurre via `window.showSection(id)` que oculta/muestra `<section>` dentro de la misma página. No cambia la URL.

---

## 1. VISIÓN

Convertir VYNTRA Solaris de "plataforma académica con buena base técnica" a:

> **"Experiencia institucional premium cinematográfica, comparable a Apple / Stripe / Linear, donde el branding solar es protagonista mediante un modelo 3D del sol."**

El sol NO es un icono estático. Es el centro narrativo, visual y emocional de toda la plataforma.

---

## 2. CAMBIO FUNDAMENTAL: LOGO 3D

### Qué hacer

Reemplazar el SVG del sol (actual en `src/components/Logo.astro` y `src/pages/index.astro`) por un **modelo 3D interactivo**.

### Opciones técnicas (evalúa ambas):

| Opción | Librería | Bundle | Interactividad | Complejidad |
|--------|----------|--------|---------------|-------------|
| **A. Three.js con @react-three/fiber** | `three`, `@react-three/fiber`, `@react-three/drei` | ~150-200 KB gzip | Rotación automática + hover + scroll parallax | Media-alta |
| **B. Spline Viewer** | `@splinetool/runtime` o `@splinetool/viewer` | ~200-300 KB gzip | Cargar .spline exportado, rotación automática | Baja-media |

### Recomendación

Usa **@react-three/fiber** porque:
- Es nativo React/Astro → no depende de Spline editor
- Control total sobre animaciones (GSAP puede controlar uniforms)
- Bundle tree-shakeable
- Puedes integrar con ScrollTrigger para animar la esfera 3D al hacer scroll

### Especificaciones del modelo

- **Forma:** Esfera solar con textura procedural (no imagen PNG)
  - Shader con ruido para simular superficie solar (fractal noise/turbulence)
  - Corona / glow dinámico (post-processing o shader transparente)
  - Partículas orbitando (opcional, para landing)
- **Animación base:** Rotación lenta continua (`rotation.y += 0.001`)
- **Interacción:**
  - Hover: leve escala + glow increase
  - Scroll (landing): posición Y controlada por ScrollTrigger
  - Click (en dashboard): redirige a inicio
- **Dark mode:** La textura debe verse bien en ambos temas (más brillante en dark)

### Integración con Astro

```astro
---
// client:load para que Three.js se monte solo en cliente
import SolarSphere from '@components/SolarSphere'
---
<SolarSphere client:load />
```

El componente `SolarSphere.astro` importa un wrapper React (`<Canvas>` de R3F) envuelto en un componente Astro `client:load`. Alternativa: componente vanilla Three.js si prefieres evitar React en el cliente.

---

## 3. NARRATIVA DE LA LANDING (REFUNDICIÓN COMPLETA)

La landing actual tiene 4 etapas. Queremos una experiencia más cinematográfica:

### Estructura propuesta (~500vh de scroll)

| Escena | % Scroll | Qué ocurre | Elemento 3D |
|--------|----------|------------|-------------|
| **Cortina** | 0-5% | Fade from black. Logo VYNTRA aparece centrado, tracking amplio | Sol 3D inicia apagado |
| **Revelación** | 5-20% | Sol se enciende (glow shader animation), nombre completo "VYNTRA Solaris" aparece. Hero text fade-in. | Sol pasa de oscuro a brillante, rotación speed baja → alta |
| **Estadísticas** | 20-35% | Sol se desplaza a la izquierda. Stats aparecen a la derecha con stagger. | Sol sigue rotando, ahora más pequeño, posición fija |
| **Features** | 35-55% | Sol se mueve arriba. Features grid aparece con stagger. Partículas se esparcen. | Sol más brillante, partículas orbitantes emanan |
| **Noticias** | 55-75% | Sol se centra y escala. Noticias aparecen debajo. | Sol escala a 1.2x, glow máximo |
| **CTA Final** | 75-100% | Sol sube. CTA masivo centrado con parallax. | Sol se eleva lentamente hasta el horizonte |

### Elementos que se mantienen

- Grid dots (fondo)
- Noise overlay (SVG fractal)
- `prefersReducedMotion` respetado
- Cleanup en `beforeunload`

### Elementos que se eliminan

- El SVG de círculos concéntricos alrededor del logo (reemplazado por corona 3D real)
- La animación `animate-spin-slow` en SVG (no necesaria con modelo 3D)

### Elementos nuevos

- Transiciones de cámara (efecto parallax con la cámara de Three.js)
- Partículas system (Three.js Points) que emanan del sol durante scrolleo
- Post-processing: bloom/unreal bloom en el sol para glow real

---

## 4. SISTEMA DE MOTION (REFINAR)

El sistema actual (`--ease-*`, `--t-*` en `:root`) es correcto. Mejorar:

### Añadir tokens de 3D

```css
:root {
  --camera-fov: 45deg;
  --particle-count: 200;
  --glow-intensity: 0.6;
  --rotation-speed: 0.001;
}
```

### Página landing

TODA animación debe pasar por GSAP ScrollTrigger como timeline único.
No crear más de un ScrollTrigger por sección.

### Dashboards

Las animaciones deben ser CSS-first (no GSAP en dashboards a menos que sea estrictamente necesario).
La excepción: entrada de cards (`card-stagger`) usa CSS puro.

### Regla de oro

> Si puede hacerse con CSS + `transition`, NO uses JS.

---

## 5. LANDING — CHECKLIST DE REEMPLAZO

| Elemento actual | Reemplazo | Responsable |
|----------------|-----------|-------------|
| `Logo.astro` (SVG) | `SolarSphere.astro` (Three.js) | Diseñador 3D |
| `#sol` (div, posicionado con GSAP) | Malla Three.js posicionada vía uniforms | Motion dev |
| `animate-spin-slow` SVG | Rotación nativa Three.js | Motion dev |
| Círculos concéntricos SVG | Corona shader en Three.js | Shader artist |
| `bg-brand-gold/8 blur-[130px]` | Post-processing bloom real | 3D dev |
| Hero text (H1) | Sin cambios (solo animación mejorada) | — |
| Stats cards | Sin cambios estructurales | — |
| Features grid | Sin cambios estructurales | — |
| Notices grid | Sin cambios estructurales | — |
| CTA final | Sin cambios estructurales | — |
| Progress bar | Conservar | — |
| Floating CTA | Conservar | — |

---

## 6. DASHBOARDS — MANTENER, NO REDISEÑAR

Los dashboards NO deben cambiar estructuralmente.

Solo aplicar:

| Componente | Mejora |
|-----------|--------|
| Sidebar | El logo VYNTRA actual → versión 3D renderizada como favicon/webp estático (no Three.js en dashboard pesado) |
| Topbar | El breadcrumb podría incluir un mini glow solar |
| Hero cards (bienvenida) | Gradiente existente es suficiente |
| AIChat | Sin cambios (ya tiene section context + placeholder dinámico + msg fade-in) |

**Regla:** El 3D vive en la landing. En dashboards, usa una imagen `.webp` pre-renderizada del modelo 3D como logo para no cargar Three.js en páginas internas.

---

## 7. PALETA DE COLOR (MANTENER)

La paleta Solaris actual NO cambia. Usa las variables existentes:

```
--brand-maroon:       #6B1A1A
--brand-maroon-light: #8B2A2A
--brand-maroon-dark:  #4A0E0E
--brand-gold:         #F5A623
--brand-gold-light:   #FFD166
--brand-gold-dark:    #C47F0A
--brand-amber:        #FF8C00
--brand-ember:        #E8650A
--brand-danger:       #DC2626
--brand-success:      #34D399
--solar-cream:        #FFFBF0
```

El 3D debe usar estos colores:

- **Superficie solar (día):** degradado de `--brand-maroon` (polos) a `--brand-gold` (centro)
- **Superficie solar (noche/dark):** `--brand-ember` con glow `--brand-gold-light`
- **Corona/glow:** `--brand-gold` con opacidad variable
- **Partículas:** `--brand-gold-light` → `--brand-amber` según distancia

---

## 8. RESTRICCIONES (NO NEGOCIABLE)

1. **Stack principal:** Astro v5 (static) + Tailwind v3. No cambiar.
2. **Netlify:** El build debe seguir siendo compatible con output static.
3. **Backend endpoints:** No tocar. Cero cambios en llamadas API.
4. **Auth:** httpOnly cookie + localStorage auxiliar. No cambiar.
5. **Chart.js:** Sigue siendo lazy via dynamic import. NO cargar globalmente.
6. **AIChat:** No cambiar lógica SSE. Preservar AbortController + Stop button.
7. **WsRiskAlert:** No cambiar WebSocket lógica ni cleanup.
8. **TypeScript:** `npm run check` debe dar 0 errors, 0 warnings.
9. **Build:** `npm run build` debe pasar sin errores.
10. **3D solo en landing:** Usar imagen `.webp` pre-renderizada para dashboards.
11. **Bundle:** El chunk de Three.js no debe superar 250 KB gzip. Si excede, implementar lazy loading con `import()`.

---

## 9. POSIBLES RIESGOS Y MITIGACIONES

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Three.js aumenta bundle landing | Alto | Tree-shaking + dynamic import del Canvas. No incluir OrbitControls en producción. |
| Compatibilidad WebGL en navegadores antiguos | Medio | Fallback a SVG animado si WebGL no está disponible. Detectar con `detect-gpu` o similar. |
| ScrollTrigger + Three.js conflicto de render loop | Medio | Usar `useFrame` de R3F, no crear loop propio. ScrollTrigger solo modifica uniforms/posición. |
| Rendimiento en mobile con partículas | Alto | Reducir `--particle-count` a 50 en mobile. Desactivar post-processing (bloom). `gsap.matchMedia()` para mobile. |
| Dark mode inconsistente con textura 3D | Medio | Pasar `--progress` y modo actual al shader como uniform. Shader debe reaccionar a ambos temas. |

---

## 10. PLAN DE TRABAJO SUGERIDO

| Fase | Duración | Output |
|------|----------|--------|
| **F1 — Prototipo 3D** | 2h | Esfera con textura procedural + rotación en `public/` como HTML standalone |
| **F2 — Integración landing** | 2h | SolarSphere.astro reemplaza Logo.astro en index.astro. GSAP controla posición Y. |
| **F3 — Partículas + glow** | 1.5h | Sistema de partículas, post-processing bloom |
| **F4 — Teaser webp para dashboards** | 0.5h | Render estático del modelo 3D → `.webp` → reemplazar logo SVG en Sidebar.astro |
| **F5 — QA final** | 1h | `npm run build` + `npm run check` + test en mobile + reduced motion + dark mode |

**Total estimado:** ~7 horas

---

## 11. REFERENCIAS VISUALES

| Inspiración | Por qué |
|-------------|---------|
| [Apple Vision Pro landing](https://www.apple.com/apple-vision-pro/) | Narrativa scroll-driven con producto 3D como protagonista |
| [Linear.app](https://linear.app/) | Microinteracciones premium, diseño sobrio |
| [Stripe docs](https://stripe.com/docs) | Jerarquía visual, glassmorphism aplicado a dashboards |
| [Solar Orbiter ESA](https://www.esa.int/Science_Exploration/Space_Science/Solar_Orbiter) | Textura solar real como referencia para shader |
| [React Three Fiber showcase](https://docs.pmnd.rs/react-three-fiber/getting-started/examples) | Técnica de integración React/Three |

---

## 12. OUTPUT ESPERADO

Al finalizar, la IA debe devolver:

1. **Archivos nuevos:** `src/components/SolarSphere.astro` (o componente Three.js equivalente)
2. **Archivos modificados:** `src/pages/index.astro`, `src/components/Logo.astro` (o reemplazado), `src/styles/theme.css` (si añade tokens)
3. **Archivos eliminados:** El SVG de `Logo.astro` si es reemplazado completamente
4. **Prueba de build:** `npm run build` exitoso
5. **Prueba de type check:** `npm run check` exitoso
6. **Métrica de bundle:** Tamaño del chunk Three.js

---

*Este brief asume que leíste `docs/FRONTEND_COMPLETO.md` como fuente de verdad del estado actual.*
*Si hay conflicto entre este brief y FRONTEND_COMPLETO.md, prevalece FRONTEND_COMPLETO.md.*
