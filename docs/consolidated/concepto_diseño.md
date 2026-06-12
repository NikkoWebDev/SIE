# VYNTRA Solaris — Concepto de Diseño

> Documento de identidad visual. Define la filosofía, decisiones y reglas que gobiernan cada píxel.

---

## 1. Filosofía central

### "El Sol como protagonista"

VYNTRA Solaris gira en torno a un concepto: **el sol como metáfora de la educación**. Así como el sol ilumina, nutre y da vida, la educación ilumina mentes, nutre el futuro y da propósito. El logo — un sol dorado sobre un libro abierto — encarna esta idea en cada página.

### Principios rectores

| Principio | Significado | Manifestación |
|-----------|------------|---------------|
| **Un solo sol** | No duplicar, no distraer | Una sola instancia del Logo por página, nunca repetido |
| **El sol viaja** | Guía el ojo, da ritmo al scroll | GSAP ScrollTrigger mueve el logo por la pantalla |
| **Contenido orbita** | La info aparece alrededor, no compite | Stats, features, notices se revelan en posiciones relativas al sol |
| **Solar technocracy** | Cálido pero preciso, humano pero técnico | Paleta maroon + dorado, tipografía Fraunces editorial, grid riguroso |
| **Claridad ante todo** | Sin ruido visual innecesario | Modo claro por defecto, espacios generosos, jerarquía clara |

---

## 2. Paleta de color

### Modo claro (principal)

```
Fondo principal:   #FFFBF0  (solar cream — cálido, no blanco puro)
Fondo secundario:  #FFF8E7  (ligeramente más crema)
Texto principal:   #2D1B0A  (marrón muy oscuro, no negro)
Texto secundario:  #7A6254  (marrón medio)
Texto terciario:   #A89080  (marrón claro, para labels y meta)
Bordes:            rgba(107,26,26,0.06)  (maroon casi invisible)
```

### Acentes

```
Maroon (brand):    #6B1A1A  → #8B2A2A (light) → #4A0E0E (dark)
  Uso: botones CTA, gradientes de header, sidebar activo, títulos destacados

Gold (solar):      #F5A623  → #FFD166 (light) → #C47F0A (dark)
  Uso: el logo, elementos decorativos, highlights, badges, hover states

Semánticos:
  Success: #34D399  (aprobado, al día)
  Danger:  #DC2626  (en riesgo, error, mora)
  Info:    #3B82F6  (datos neutros)
```

### Modo oscuro

```
Fondo:             #0D0A08  (warm charcoal, no negro puro)
Texto:             #FFFBF0  (solar cream invertido)
Gold glow:         rgba(245,166,35,0.08-0.12)  (más sutil que en claro)
Maroon:            se reemplaza por gold en elementos activos
```

### Regla de uso

- **NO usar negro puro `#000` ni blanco puro `#fff`** en ningún lado. Siempre usar los tokens del sistema.
- Los gradientes siempre van de maroon→maroon-dark o gold→amber. Nunca mezclar maroon con gold en el mismo gradiente de botón.
- El dorado es un **acento**, no un color de fondo. Usarlo con moderación.

---

## 3. Tipografía

### Jerarquía

| Nivel | Font | Weight | Tamaño | Uso |
|-------|------|--------|--------|-----|
| Display | Fraunces | 900 (black) | clamp(2.8rem, 10vw, 6.5rem) | Título hero "VYNTRA Solaris" |
| H1 | Fraunces | 700 (bold) | 2-2.5rem | Títulos de sección en dashboard |
| H2 | Fraunces | 700 | 1.25-1.5rem | Subtítulos |
| H3 | Fraunces | 700 | 1rem | Cards, features |
| Body | DM Sans | 400 | 14-16px | Texto corrido |
| Body small | DM Sans | 400 | 12px | Descripciones secundarias |
| Label | DM Sans | 600 (semibold) | 10px | Labels uppercase, badges |
| Data | Fraunces | 800 (extrabold) | 2-5rem | Números en stats cards |

### Reglas

- Fraunces **solo para headings y datos numéricos**. Nunca para body text.
- DM Sans para **todo el cuerpo de texto**, labels, formularios.
- Los labels siempre van en **uppercase + tracking-wider + 10px**. Sin excepción.
- NO usar más de 3 tamaños distintos en una misma vista.

---

## 4. El Logo — Anatomía

```
         ☀ SOL CENTRAL
        / | \
       /  |  \   ← 8 rayos corona (alternan 75px y 68px)
      /   |   \
     /    |    \
    ┌─────────────┐
    │  📖 LIBRO   │  ← base maroon con páginas crema
    │  ▎  ▎ ▎ ▎  │  ← bookmark dorado cayendo del centro
    └──────┬──────┘
           │
    Monograma "V" dentro del núcleo solar
```

### Especificaciones

- ViewBox: `0 0 256 206`
- Sin fondo (transparente)
- Gradiente solar: `#F5A623` → `#FFD166` → `#C47F0A`
- Gradiente libro: `#6B1A1A` → `#8B2A2A`
- Páginas: `#FFFBF0` con 15-20% opacidad
- Drop-shadow dorado en todas las instancias

### Reglas de uso del logo

1. **Solo una instancia por página.** Si necesitás una segunda, algo está mal.
2. **Siempre con drop-shadow dorado** (`drop-shadow(0 0 Xpx rgba(245,166,35,0.X))`)
3. **Tamaños predefinidos:** 170px (hero), 140px (dashboard/stage), 130px (login), 110px (compacto)
4. **Nunca rotarlo ni deformarlo.** Solo escalar proporcionalmente.
5. **Nunca ponerlo sobre fondo oscuro** sin el glow correspondiente.

---

## 5. Layout y Espaciado

### Grid system

```
Contenedor máximo: 1440px (dashboards), sin límite en landing
Sidebar: 240px (w-60)
Columnas: Tailwind grid-cols-{2,3,4} según contenido
Gap: 12-20px (gap-3 a gap-5)
```

### Espaciado vertical (landing)

```
Hero/stage:     100svh (viewport height, respeta browser chrome)
Spacers:        80-110vh (generan altura de scroll para el timeline)
Padding cards:  16-20px (p-4 a p-5)
Entre secciones: 20px (space-y-5)
```

### Espaciado (dashboard)

```
Padding main:   px-3 sm:px-5 lg:px-8 py-4 sm:py-6
Entre cards:    gap-3 sm:gap-5
Card padding:   p-4 sm:p-5
```

### Reglas

- **No usar `min-h-screen` en cada sección** — genera páginas vacías. Solo en el hero/stage.
- Los spacers del journey son `height: Xvh` (divs vacíos), no padding ni margin.
- Mobile-first: los breakpoints arrancan en 375px, no en desktop.

---

## 6. Animaciones y Movimiento

### Filosofía de movimiento

> "Cada animación debe servir a la narrativa. Si no cuenta algo, no debería estar."

### Tipos de animación

| Tipo | Tecnología | Uso |
|------|-----------|-----|
| Film-roll hero | GSAP ScrollTrigger | Texto del hero rota en 3D y desaparece al hacer scroll |
| Solar journey | GSAP ScrollTrigger (scrub) | El logo se reposiciona con el scroll |
| Scroll reveals | CSS `animation-timeline: view()` | Opcional, fallback a IntersectionObserver |
| Logo breathe | CSS `@keyframes` | Pulso sutil del logo (4s loop) |
| Section transitions | CSS `section-enter` | Fade + slide-up al cambiar de sección en dashboard |
| Hover states | Tailwind `hover:` | Escala sutil (-translate-y-1), shadow aparece |
| Toast | CSS `toastSlideIn` | Slide desde abajo con spring easing |

### Reglas de animación

1. **`prefers-reduced-motion: reduce` detiene TODO.** Sin excepción.
2. **Solo animar `transform` y `opacity`.** Nunca width, height, top, left, margin.
3. **GSAP con `scrub: true`** para scroll-linked. Sin `scrub` para triggers discretos.
4. **Máximo 1 timeline de GSAP activo a la vez.**
5. **Los hover NO deben disparar layout shifts.**
6. **Duración máxima de cualquier animación: 1.5s.** Ideal: 0.3-0.6s.

### Curvas de easing

```
GSAP power2.out     → entrada suave (reveals)
GSAP power3.inOut   → transiciones dramáticas (film-roll)
GSAP back.out(1.7)  → overshoot elástico (CTA final)
GSAP none           → scrub lineal (logo viajero)
CSS cubic-bezier(0.22,1,0.36,1) → section transitions
```

---

## 7. Componentes — Anatomía visual

### Card (stats, features, notices)

```html
<div class="bg-white/70 backdrop-blur border border-border rounded-xl p-4
            hover:shadow-md hover:-translate-y-0.5 transition-all duration-300">
  <!-- Contenido -->
</div>
```

**Reglas:**
- Esquinas: `rounded-xl` (12px) o `rounded-2xl` (16px) para cards principales
- Borde: `border-border` (maroon 6% opacity) — NUNCA sin borde
- Hover: sombra sutil + levantar 2px — sin cambio de color de fondo
- Fondo: blanco con 60-70% opacidad + backdrop-blur (efecto vidrio)

### Botones

```html
<!-- Primario (CTA) -->
<a class="bg-gradient-to-r from-brand-maroon to-brand-maroon-dark text-white
          rounded-xl hover:shadow-[0_0_35px_rgba(107,26,26,0.2)] hover:scale-105">

<!-- Secundario (outline) -->
<button class="bg-solar-100 border border-border rounded-lg hover:bg-solar-200">
```

**Reglas:**
- Primario: gradiente maroon, texto blanco, sombra maroon en hover
- El dorado SOLO se usa en botones del login (contraste con fondo crema)
- Altura mínima: 44px (touch target)
- Padding horizontal: mínimo 16px

### Inputs

```html
<input class="w-full bg-[var(--input-bg)] border border-[var(--input-border)]
              rounded-lg px-3.5 py-2.5 text-sm
              focus:border-brand-maroon/30 focus:shadow-[0_0_0_3px_var(--input-focus-ring)]" />
```

**Reglas:**
- Fondo: `var(--input-bg)` (maroon 3% en claro, gold 4% en oscuro)
- Focus: borde maroon + anillo de 3px con opacidad
- Placeholder: `text-text-tertiary/40`
- Height: mínimo 44px en mobile

### Skeleton loading

```html
<div class="skeleton-shimmer h-4 w-3/4 rounded"></div>
```

Animación `shimmer` global: gradiente se mueve de derecha a izquierda en 1.8s.

---

## 8. Responsive — Breakpoints

| Nombre | Min-width | Uso típico |
|--------|-----------|------------|
| xs | 380px | Ajustes mínimos de padding |
| sm | 640px | Grid de 2 columnas |
| md | 768px | Sidebar visible |
| lg | 1024px | Grid de 3 columnas, sidebar + contenido |
| xl | 1280px | Contenido más ancho |
| 2xl | 1440px | Ancho máximo de main content |

### Comportamientos responsive clave

```
Mobile (<768px):
  - Sidebar oculto (translate-x-full), toggle hamburguesa
  - Grid de 1 columna (stats, features, notices)
  - Toast full-width
  - Touch targets 44×44px mínimo
  - Input font-size 16px (previene zoom iOS)

Tablet (768-1023px):
  - Sidebar visible
  - Grid de 2 columnas para cards
  - Navegación más compacta

Desktop (≥1024px):
  - Sidebar fijo 240px
  - Grid de 3-4 columnas
  - Landing: sticky side panel + texto scroll
```

---

## 9. Accesibilidad

### Checklist aplicado

- [x] `prefers-reduced-motion` detiene TODAS las animaciones
- [x] Focus visible: anillo dorado 2px en `:focus-visible`
- [x] Skip link: "Saltar al contenido" en BaseLayout
- [x] ARIA: `role="navigation"`, `aria-label`, `aria-current="page"`, `aria-live="polite"`
- [x] Touch targets ≥44×44px en mobile
- [x] Contraste: texto #2D1B0A sobre #FFFBF0 = ratio 12.5:1 (AAA)
- [x] Gráficos Chart.js con `role="img"` y `aria-label`
- [x] Toast HTML-escaped (usa `textContent`, no `innerHTML`)
- [x] SEO: Schema.org School + WebSite en landing, sitemap.xml

---

## 10. Lo que NUNCA se hace

1. **Duplicar el logo.** Una página = un logo. Sin excepciones.
2. **Usar negro puro o blanco puro.** Siempre usar los tokens del sistema.
3. **Animar `width`, `height`, `top`, `left`, `margin`, `padding`.** Solo `transform` y `opacity`.
4. **Crear páginas con scroll infinito vacío.** Si no hay contenido, no hay sección.
5. **Mezclar maroon y gold en gradientes de UI funcional.** El dorado es acento, el maroon es acción.
6. **Hardcodear URLs de API.** Siempre usar `import.meta.env.PUBLIC_API_URL`.
7. **Olvidar el `prefers-reduced-motion`.** Es accesibilidad, no opcional.
8. **Usar más de 3 tamaños de fuente en una misma vista.**
9. **Poner bordes gruesos.** El borde máximo es 1px, opacidad 6-12%.
10. **Dejar animaciones en producción sin testear en mobile real.**
