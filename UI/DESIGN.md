---
name: Obsidian Glass
colors:
  surface: '#121414'
  surface-dim: '#121414'
  surface-bright: '#37393a'
  surface-container-lowest: '#0c0f0f'
  surface-container-low: '#1a1c1c'
  surface-container: '#1e2020'
  surface-container-high: '#282a2b'
  surface-container-highest: '#333535'
  on-surface: '#e2e2e2'
  on-surface-variant: '#e2bfb9'
  inverse-surface: '#e2e2e2'
  inverse-on-surface: '#2f3131'
  outline: '#a98984'
  outline-variant: '#5a413d'
  surface-tint: '#ffb4a8'
  primary: '#ffb4a8'
  on-primary: '#690000'
  primary-container: '#800000'
  on-primary-container: '#ff8371'
  inverse-primary: '#b22b1d'
  secondary: '#ffdf9d'
  on-secondary: '#3f2e00'
  secondary-container: '#f9bd00'
  on-secondary-container: '#694e00'
  tertiary: '#c9c6c8'
  on-tertiary: '#313032'
  tertiary-container: '#3d3c3e'
  on-tertiary-container: '#a9a6a8'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad4'
  primary-fixed-dim: '#ffb4a8'
  on-primary-fixed: '#410000'
  on-primary-fixed-variant: '#8f0f07'
  secondary-fixed: '#ffdf9d'
  secondary-fixed-dim: '#f9bd00'
  on-secondary-fixed: '#251a00'
  on-secondary-fixed-variant: '#5b4300'
  tertiary-fixed: '#e5e1e4'
  tertiary-fixed-dim: '#c9c6c8'
  on-tertiary-fixed: '#1c1b1d'
  on-tertiary-fixed-variant: '#474648'
  background: '#121414'
  on-background: '#e2e2e2'
  surface-variant: '#333535'
  obsidian-base: '#040405'
  glass-border: rgba(255, 255, 255, 0.08)
  success-green: '#4CAF50'
  critical-red: '#BA1A1A'
  gold-accent: '#FDC003'
  maroon-brand: '#800000'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  sidebar-width: 280px
  mobile-nav-height: 72px
  gutter: 24px
  container-margin: 32px
  glass-padding: 1.5rem
---

## Brand & Style
The design system for SIE (Sistema de Información Estudiantil) is an advanced **Glassmorphism** implementation tailored for a modern educational environment. It moves away from traditional, flat institutional layouts toward a futuristic, immersive experience.

The visual narrative centers on depth and transparency. By utilizing an **Obsidian Dark** base, the UI feels like a high-performance dashboard. The brand evokes a sense of prestige, technological advancement, and academic excellence. Interactions are defined by "Organic Elasticity," using high-tension cubic-beziers to create a tactile, liquid-like feel when elements appear or transition.

## Colors
The palette is rooted in an ultra-dark **Obsidian** foundation (#040405), providing the necessary contrast for translucent glass layers.

- **Primary & Secondary:** The Brand Maroon serves as the primary action color for high-importance interactions, while Radiant Gold is used for secondary accents, icons, and highlighting special achievements.
- **Semantic Logic:** Grades are color-coded for instant cognitive processing. Success Green (#4CAF50) is applied to all passing statuses (>= 3.5). Critical Danger Red (#BA1A1A) is reserved for failing marks (< 3.5), enhanced with a subtle pulsing radial glow to denote urgency.
- **Translucency:** Backgrounds are never solid. Surfaces use a layered alpha channel (e.g., `rgba(255, 255, 255, 0.03)`) to maintain the glass effect against the dark background.

## Typography
**Plus Jakarta Sans** is the sole typeface, chosen for its modern, geometric clarity and excellent legibility in dark environments. 

- **Hierarchies:** Headlines use heavier weights (700-800) with tighter letter spacing to create a professional, "newsroom" editorial feel.
- **Tone:** Copy should be in formal, professional Latin American Spanish (e.g., "Rendimiento Académico" instead of "Notas").
- **Readability:** Body text maintains a slightly higher line-height to prevent eye fatigue during long sessions of grade review or data entry.

## Layout & Spacing
The layout utilizes a flexible spacing system that prioritizes "breathing room" around glass panels to allow background blurs to shine.

- **Desktop:** Features a **Sleek Left Glass Sidebar** (280px) that remains semi-transparent, allowing content to bleed slightly behind it.
- **Mobile:** Transition to a **Floating Pill Bottom Nav**. This element should be detached from the screen edges with a 16px margin, appearing to float above the content.
- **Grid:** A 12-column grid is used for desktop dashboards, collapsing to a single column on mobile. Spacing between panels (gutters) is fixed at 24px to maintain structural integrity.
- **Animations:** All layout transitions must use `cubic-bezier(0.34, 1.56, 0.64, 1)` for an elastic, bouncy feel.

## Elevation & Depth
Depth is not achieved through shadows, but through **refraction and layering**.

1.  **Base Layer:** The Obsidian (#040405) floor.
2.  **Surface Layer:** Semi-transparent panels with `backdrop-filter: blur(20px)` and a white-tinted opacity of 3-5%.
3.  **Borders:** Every glass element must have a 1px solid border using `rgba(255, 255, 255, 0.08)`. This "inner glow" border defines the shape against the dark background.
4.  **Interactive State:** Upon hover or focus, the glass panel's background opacity increases to 8%, and the border brightness increases.

## Shapes
The shape language is organic and approachable. 

- **Standard Elements:** Use `rounded-lg` (1rem) for most glass panels and containers.
- **Interactive Elements:** Buttons and floating navigation bars use `rounded-xl` (1.5rem) or full pill shapes to signify touch-friendly surfaces.
- **Strictness:** Avoid sharp corners (0px) entirely, as they conflict with the "organic" and "elastic" motion profile of the design system.

## Components
- **Glass Cards:** The core container. Must feature the 20px blur and the 1px translucent border. For grades < 3.5, the card gains a subtle `box-shadow: 0 0 15px rgba(186, 26, 26, 0.2)` that pulses.
- **Buttons:**
    - **Primary:** Solid Brand Maroon with white text.
    - **Secondary/Glass:** Transparent background, 1px white border (0.2 alpha), and heavy blur.
- **Chips:** Used for "Subject Categories" or "Status." They should be pill-shaped with high-contrast labels.
- **Input Fields:** Darkened glass surfaces (`rgba(0,0,0,0.3)`) with the gold accent color used for the active focus ring.
- **Floating Pill Nav:** A detached bottom navigation bar for mobile. It must contain 4-5 icons, using a "frosted glass" effect that allows the underlying page content to scroll behind it with high distortion.
- **Lists:** Academic records are presented in "Intercalated Glass Rows," where every other row has a slightly higher transparency to aid vertical scanning.