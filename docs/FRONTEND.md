# VYNTRA Academic — Frontend Conventions

## Framework
- Astro v5 with `@astrojs/netlify` adapter (static site generation)
- Tailwind v3 for layout utilities only (not for styling)
- Chart.js v4 via CDN for charts

## Design System
All CSS lives in `src/styles/theme.css`:
- CSS custom properties for everything (spacing, radius, easing, colors, shadows)
- Theme classes: `.card-float`, `.input-apple`, `.btn-apple`, `.glass`, `.sidebar`, etc.
- Dark/light via `.dark` class on `<html>` element
- Theme persisted to `localStorage('vyntra-theme')`, respects `prefers-color-scheme`

### Responsive Breakpoints
- Mobile: `max-width: 480px` (tight padding, single column grids)
- Tablet: `max-width: 768px` (sidebar overlay, 2-col grids)
- Desktop: `min-width: 1024px` (full sidebar visible, multi-col)

### Responsive Helpers
- `.hide-mobile` — hidden on mobile, visible ≥768px
- `.show-mobile` — visible on mobile, hidden ≥768px

### Fluid Typography
- `clamp(min, preferred, max)` for all heading sizes
- Body: `clamp(0.9rem, 1.1vw, 1rem)`

### Safe Areas
- `env(safe-area-inset-*)` for notched devices used in all fixed elements

## Pages

### estudiante.astro (Student Dashboard)
- Standalone page with its own sidebar (`.est-sidebar`)
- Uses `Layout.astro` only for HTML shell (<head>, fonts, Chart.js, session.js) — passes `sinMenu={true}`
- Sections: Inicio (grades/averages), Exámenes, Votaciones, Aula Virtual, Tareas, Boletín
- Features: live clock, online indicator, exam modal with anti-fraud timer, auto-save every 30s

### docente.astro (Teacher Dashboard)
- Standalone page (does NOT use Layout.astro)
- Sections: Panel (overview), Control de Notas (grade form), Materiales (upload), Alertas
- Sidebar: `.teacher-sidebar` with overlay
- Grade form: 2-col grid, student select, subject select, score input, type select
- Upload: file dropzone → AI extract → MD to Cloudinary + file to Google Drive

### admin.astro (Admin Dashboard)
- Standalone page (does NOT use Layout.astro)
- Sections: Dashboard (stats), Estudiantes (table), Docentes, Materias, Avisos, Elecciones
- Sidebar: `.admin-sidebar` with overlay
- Features: CRUD students/teachers, create subjects, publish notices, manage elections

### login.astro
- Split layout: brand panel (hidden <1024px) + form panel
- Segmented tab control (Estudiante / Personal)
- Apple-style form inputs with icon prefixes

### index.astro (Landing)
- Hero with grid-dots, stats grid, feature cards, notices section

## Components

### AIChat.astro
- Fixed bottom-right, role-based (student/teacher/admin)
- Tailwind + inline styles for positioning
- Full-width on mobile: `w-[calc(100vw-2rem)]`
- SSE streaming, context-aware (grades, risk, financial data)

### WsRiskAlert.astro
- Fixed top-right toast container
- WebSocket client with auto-reconnect
- Audio alert via Web Audio API oscillator
- Max-width constrained for mobile

## Data Fetching
- `apiFetch()` in `src/scripts/api.ts` — shared fetch with 401 auto-redirect
- Fallback: direct `fetch(apiUrl + '/api/...')` with Bearer token from localStorage
- `PUBLIC_API_URL` env var or fallback `http://localhost:8000`

## API Endpoints (Frontend-facing)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login with ID + password |
| `/api/auth/register` | POST | Register (admin only) |
| `/api/auth/oauth/google` | POST | Google OAuth login |
| `/api/auth/forgot-password` | POST | Send recovery email |
| `/api/grades?student_id=X` | GET | Student grades |
| `/api/teacher/submit-grade` | POST | Submit grade |
| `/api/students/risk` | GET | Risk students list |
| `/api/notices` | GET | Active notices |
| `/api/admin/stats` | GET | System statistics |
| `/api/admin/create-account` | POST | Admin creates user |
| `/api/upload-material` | POST | Upload educational material |
