# VYNTRA — Comprehensive Bug Audit

> Generated: 2026-06-05
> Scope: All pages, layouts, components, configs, CSS, scripts

---

## 🔴 CRITICAL — Will Cause Breaks

### 1. Admin search mutates cache destructively
**File:** `src/pages/admin.astro:311-314`
**Code:**
```js
cache.students = filtered; renderStudents();
```
**Problem:** Replaces full student list with filtered subset. Second search re-filters already-filtered list. Data is permanently lost without page reload.
**Fix:** Keep a `_fullStudents` parallel cache.

### 2. Admin grade + payment filter selects do nothing
**File:** `src/pages/admin.astro:47-48`
**Problem:** `<select id="filter-grade">` and `<select id="filter-payment">` exist in HTML but have zero event handlers. User changes them — nothing happens.
**Fix:** Add `change` event listeners.

### 3. AIChat save corrupts assistant messages
**File:** `src/components/AIChat.astro:147-152,186-189,223`
**Problem:** `saveMessages()` queries `[data-msg-role]` + `[data-msg-text]` on the same element. But `data-msg-role` is set on the inner bubble (line 186) while `data-msg-text` is set on the outer wrapper (line 223). On page reload, assistant messages save as `content: null` → blank bubbles.
**Fix:** Set both attributes on the wrapper `div`.

### 4. Student dashboard calls teacher schedule endpoint
**File:** `src/pages/estudiante.astro:460`
**Code:**
```js
apiFetch('/api/teacher/schedule')
```
**Problem:** Student section requests teacher schedule → 404 or wrong data.
**Fix:** Use student-specific endpoint (e.g., `/api/schedule?student_id=X`).

### 5. `@keyframes shimmer` never defined
**File:** `src/styles/theme.css:175`
**Code:**
```css
.skeleton-shimmer {
  animation: shimmer 1.8s ease-in-out infinite;
}
```
**Problem:** `@keyframes shimmer` block is missing. Skeleton loading states have zero animation.
**Fix:** Add the keyframes definition.

---

## 🟠 HIGH — Runtime Errors / Logic Bugs

### 6. `googleClientId` imported but never used
**File:** `src/pages/login.astro:5`
**Code:**
```astro
const googleClientId = import.meta.env.PUBLIC_GOOGLE_CLIENT_ID || ''
```
**Problem:** Dead import. Not referenced in template or script.

### 7. Login tab ARIA violation
**File:** `src/pages/login.astro:64-68`
**Problem:** `role="tablist"` with `role="tab"` but zero `role="tabpanel"` elements. Form never changes between tabs. Screen readers detect empty tab structure.

### 8. Login form `novalidate` with no JS fallback
**File:** `src/pages/login.astro:70`
**Problem:** `novalidate` disables browser validation. If JS fails (slow network, CDN, ad-blocker), form submits empty with no feedback.

### 9. CSP `'unsafe-inline'` on all scripts
**File:** `src/layouts/BaseLayout.astro:22-23`
**Problem:** Both dev and prod CSP include `'unsafe-inline'` for scripts. Reduces XSS protection. Required for `define:vars`/`is:inline` but amplifies any injection.

### 10. CDN hosts in CSP script-src
**File:** `src/layouts/BaseLayout.astro:22`
**Problem:** `cdn.jsdelivr.net` and `cdnjs.cloudflare.com` in script-src. Injected scripts pointing to these CDNs would execute.

### 11. Teacher grades sheet fetches ALL students
**File:** `src/pages/docente.astro:236`
**Code:**
```js
vfetch(API, '/api/admin/students').then(function(r){return r.json()})
```
**Problem:** Downloads every student in the system, then filters client-side by grade. Won't scale beyond ~200 students.

### 12. Dashboard redirect race condition
**File:** `src/pages/dashboard.astro:13-19`
**Problem:** If `userRole` not set yet (race with login redirect after `localStorage.clear()`), user sees spinner forever. No timeout fallback.

### 13. Student ID calculation fragile
**File:** `src/pages/estudiante.astro:234-235`
**Code:**
```js
var studentId = localStorage.getItem('profile_id') || localStorage.getItem('userId')
```
**Problem:** Falls back to `userId` which may be numeric (`'1'`) rather than a proper profile UUID. Breaks API calls expecting UUID format.

---

## 🟡 MEDIUM — CSS / Responsive / UI

### 14. Mobile sidebar responsive conflict
**File:** `src/components/layout/Sidebar.astro:61`
**Code:**
```html
class="... -translate-x-full lg:translate-x-0 ..."
```
**Problem:** Tailwind's `lg:translate-x-0` has higher specificity than JS `classList.toggle()`. On window resize from mobile→desktop while menu is open, sidebar gets stuck.

### 15. `[onclick]` forces 44×44px on all elements
**File:** `src/styles/theme.css:143-144`
**Problem:** `[onclick]:not(...) { min-width:44px; min-height:44px }` applies to SVG icons, spans, and other small elements that happen to have inline onclick handlers.

### 16. Sidebar active state: border + shadow conflict
**File:** `src/styles/theme.css:227` + `Sidebar.astro:75`
**Problem:** CSS applies `box-shadow: 4px 0 0 0` for sidebar glow. ASTRO template has `border-l-[3px]`. Combined = 7px left accent bar (inconsistent 3+4px vs 3px on inactive).

### 17. Safe area padding applied globally
**File:** `src/styles/theme.css:197-199`
**Problem:** `@supports(padding: max(0px))` globally adds safe-area padding. On desktop this is 0 — no visual issue, but the selector leaks to all viewports.

### 18. Bar chart initial height is 4px
**File:** `src/pages/estudiante.astro:86`
**Code:**
```html
<div ... style="height:4px"></div>
```
**Problem:** Before data loads, period bars are 4px tall — barely visible placeholder.

### 19. Upload dropzone uses emoji icon
**File:** `src/pages/estudiante.astro:123`
**Problem:** `&#x1F4CE;` renders differently across OS/browser. SVG would be consistent.

### 20. Dead CSS `.modal-overlay`
**File:** `src/pages/login.astro:137-139`
**Problem:** Class `.modal-overlay` never used in any element. Single rule achieves nothing.

---

## 🔵 LOW — Code Quality / Duplication / Dead Code

### 21. `public/js/session.js` never loaded
**File:** `public/js/session.js`
**Problem:** Auth interceptor, wake-up ping, session check — all duplicated inline in BaseLayout/DashboardShell. This file is dead code on disk.

### 22. `src/config.ts` missing
**File:** Referenced in `AGENTS.md` but file doesn't exist.

### 23. `src/lib/utils.ts` missing
**File:** Referenced in `AGENTS.md` but file doesn't exist.

### 24. API fetch logic duplicated 3 ways
- `apiFetch()` in `estudiante.astro:245-261`
- `vfetch()` in `DashboardShell.astro:73-91`
- Raw `fetch()` in `login.astro:178`, `index.astro:286`
Different error handling, timeouts, auth checks.

### 25. Theme toggle logic duplicated 4 ways
- `Sidebar.astro` inline `<script>`
- `estudiante.astro` `setTheme()` function
- `DashboardShell.astro` `setVyntraTheme()`
- `index.astro` nav toggle
Different function names, inconsistent APIs.

### 26. Clock interval duplicated
- `DashboardShell.astro` has `startVyntraClock()` helper (never called)
- `estudiante.astro` has own inline `setInterval`
- `Topbar.astro` renders `#live-clock` for student only

### 27. Topbar mobile menu uses fragile selectors
**File:** `Topbar.astro:51-52`
**Code:**
```js
document.querySelector('[class*="sidebar-"]')
document.querySelector('[id^="sidebar-overlay-"]')
```
**Problem:** Attribute-contains selectors break if class/id naming changes.

### 28. Google Fonts: 4 families × 10 weights = ~700KB
**File:** `BaseLayout.astro:52-53`
**Problem:** No font subsetting. Every page load fetches all weights of DM Sans, Fraunces, Syne, Azeret Mono.

### 29. Admin modal close toggles `hidden`+`flex` manually
**File:** `admin.astro:134`
**Problem:** Inline `classList.add('hidden'); classList.remove('flex')` pattern duplicated on Cancel button. More brittle than a toggle helper.

### 30. Inconsistent ID fields across CRUD
**File:** `admin.astro:274-275`
**Problem:** `togglePayment` uses `s._id`, `deleteTeacher` uses `t.document_id`. Same concept, different field names.

---

## Fix Status

| # | Bug | Status |
|---|-----|--------|
| 1 | Admin cache mutation | ✅ `_fullStudents` backup + `applyFilters()` |
| 2 | Admin filter selects | ✅ `change` handlers for grade & payment selects |
| 3 | AIChat save corruption | ✅ Removed `data-msg-role` from inner bubble, only on wrapper `div` |
| 4 | Student schedule endpoint | ✅ Changed to `/api/schedule?student_id=X` |
| 5 | `@keyframes shimmer` | ✅ Added shimmer + fadeUp keyframes |
| 6 | googleClientId dead code | ✅ Removed dead import |
| 7 | Login tab ARIA | ✅ Added `role="tabpanel"` + `aria-labelledby` to form |
| 8 | Login novalidate | ✅ Removed `novalidate` attribute |
| 9 | CSP unsafe-inline | ⏳ Required for `define:vars` + `is:inline` scripts |
| 10 | CDN in CSP | ✅ Removed `cdn.jsdelivr.net` + `cdnjs.cloudflare.com` from both layouts |
| 11 | All-students fetch | 🔶 Needs backend filtering endpoint |
| 12 | Dashboard race | ✅ Added 5s timeout redirect fallback |
| 13 | Student ID fragility | ✅ Normalized short IDs with `profile_` prefix |
| 14 | Sidebar responsive | ✅ `lg:!translate-x-0` with `!important` variant |
| 15 | [onclick] 44px | ✅ Excluded SVG/path/circle/line elements |
| 16 | Sidebar border+shadow | ✅ Removed `box-shadow: 4px 0 0 0` bar (kept inset glow + border-l) |
| 17 | Safe area global | ✅ Wrapped in `@media(max-width:768px)` |
| 18 | Chart bar height | ✅ Changed initial to `4%;min-height:2px` |
| 19 | Emoji icon | ✅ Replaced with SVG upload icon |
| 20 | Dead CSS `.modal-overlay` | ✅ Removed entire `<style>` block |
| 21 | session.js dead | ✅ Wired into `BaseLayout.astro` via `<script defer>` |
| 22 | config.ts missing | ⏳ Referenced only in AGENTS.md |
| 23 | utils.ts missing | ⏳ Referenced only in AGENTS.md |
| 24 | Duplicate theme toggle | ✅ `estudiante.astro` now uses `window.setVyntraTheme` |
| 25 | Duplicate clock | ⏳ Minor — 2 lines |
| 26 | Topbar fragile selectors | ⏳ Works as-is if naming stable |
| 27 | Google Fonts weight | ⏳ Needs build-time subsetting |
| 28 | Modal close pattern | ⏳ Works, cosmetic |
| 29 | ID field inconsistency | ⏳ Backend schema decision |
| 30 | Duplicate fetch logic | ⏳ Needs centralized lib |

**Legend:** ✅ Fixed | 🔶 Needs backend/config | ⏳ Low-priority / deferred
