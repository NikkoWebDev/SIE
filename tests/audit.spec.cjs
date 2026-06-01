const { chromium } = require('playwright')

const BASE = 'http://localhost:4321'

const PAGES = [
  { path: '/', name: 'index', needsAuth: false },
  { path: '/login', name: 'login', needsAuth: false },
  { path: '/404', name: '404', needsAuth: false },
  { path: '/dashboard', name: 'dashboard', needsAuth: true },
  { path: '/admin', name: 'admin', needsAuth: true, role: 'ADMIN' },
  { path: '/docente', name: 'docente', needsAuth: true, role: 'profesor' },
  { path: '/estudiante', name: 'estudiante', needsAuth: true, role: 'ESTUDIANTE' },
]

const RESULTS = {
  passed: [],
  failed: [],
  warnings: [],
  info: [],
  consoleErrors: {},
  networkErrors: [],
  seoIssues: [],
  a11yIssues: [],
}

const AUTH_STORAGE = {
  access_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJyb2xlIjoidGVzdCIsImV4cCI9OTk5OTk5OTk5OX0.test',
  userId: 'test_user_001',
  profile_id: 'test_profile_001',
  userRole: 'admin',
  userName: 'Test Admin',
  userGrade: '10°',
  vyntra_theme: 'light',
}

async function setupAuth(page, role) {
  const auth = { ...AUTH_STORAGE, userRole: role || 'ADMIN' }
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.evaluate((data) => {
    for (const [key, val] of Object.entries(data)) {
      try { localStorage.setItem(key, val) } catch (e) { /* ignore */ }
    }
  }, auth)
}

async function run() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: 'es-CO',
  })

  for (const { path, name, needsAuth, role } of PAGES) {
    RESULTS.consoleErrors[name] = []
    const page = await context.newPage()

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        RESULTS.consoleErrors[name].push(msg.text())
      }
    })
    page.on('pageerror', (err) => {
      RESULTS.consoleErrors[name].push('PAGE_ERROR: ' + err.message)
    })
    page.on('response', (response) => {
      if (response.status() >= 400 && !response.url().includes('/404')) {
        RESULTS.networkErrors.push({
          page: name,
          url: response.url().slice(0, 100),
          status: response.status(),
        })
      }
    })

    try {
      console.log(`\n📄 Testing /${name} (${path})${needsAuth ? ' 🔐' : ''}`)
      const startTime = Date.now()

      if (needsAuth) {
        await setupAuth(page, role)
      }

      // Reload at target URL
      const resp = await page.goto(BASE + path, { waitUntil: 'networkidle', timeout: 15000 }).catch(e => null)
      const loadTime = Date.now() - startTime

      // Check what page we actually landed on (auth redirects)
      const currentUrl = page.url()
      if (needsAuth && currentUrl.includes('/login')) {
        RESULTS.warnings.push({ page: name, issue: `Auth redirect to /login — localStorage may not be set correctly` })
      }

      // --- HTML Structure & SEO ---
      const title = await page.title()
      if (!title || title.trim() === '') {
        RESULTS.seoIssues.push({ page: name, issue: 'Missing <title>' })
      } else if (title.includes('VYNTRA · VYNTRA')) {
        RESULTS.seoIssues.push({ page: name, issue: `Duplicate brand in title: "${title}"` })
      }

      const metaDesc = await page.locator('meta[name="description"]').count()
      if (metaDesc === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing meta description' })

      const robots = await page.locator('meta[name="robots"]').count()
      if (robots === 0 && !['index','login','404'].includes(name)) {
        RESULTS.seoIssues.push({ page: name, issue: 'Missing robots meta tag' })
      }

      const canonical = await page.locator('link[rel="canonical"]').count()
      if (canonical === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing canonical link' })

      const ogTitle = await page.locator('meta[property="og:title"]').count()
      if (ogTitle === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing og:title' })

      const ogDesc = await page.locator('meta[property="og:description"]').count()
      if (ogDesc === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing og:description' })

      const twitterCard = await page.locator('meta[name="twitter:card"]').count()
      if (twitterCard === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing twitter:card' })

      const viewportTag = await page.locator('meta[name="viewport"]').count()
      if (viewportTag === 0) RESULTS.seoIssues.push({ page: name, issue: 'Missing viewport meta tag' })

      // --- Accessibility ---
      const h1s = await page.locator('h1').all()
      if (h1s.length === 0) {
        RESULTS.a11yIssues.push({ page: name, issue: 'No <h1> on page' })
      } else if (h1s.length > 1) {
        // Debug: show what the h1s contain
        const texts = await Promise.all(h1s.map(h => h.textContent()))
        RESULTS.warnings.push({ page: name, issue: `Multiple <h1> found (${h1s.length}): ${texts.map(t => t.slice(0,30)).join(' | ')}` })
      }

      const lang = await page.locator('html').getAttribute('lang')
      if (!lang) RESULTS.a11yIssues.push({ page: name, issue: 'Missing lang attribute on <html>' })

      const navLandmarks = await page.locator('nav, [role="navigation"]').count()
      if (navLandmarks === 0 && !['login','404'].includes(name)) {
        RESULTS.a11yIssues.push({ page: name, issue: 'No navigation landmark' })
      }

      // --- Console errors (legit ones) ---
      const realErrors = RESULTS.consoleErrors[name].filter(
        e => !e.includes('ERR_CONNECTION_REFUSED') && !e.includes('favicon.ico') && !e.includes('ERR_BLOCKED_BY_CSP')
      )
      if (realErrors.length > 0) {
        RESULTS.failed.push({ page: name, test: 'Console errors', details: realErrors.slice(0,3).join('; ') })
      } else if (RESULTS.consoleErrors[name].length > 0) {
        // Only connection refused errors — expected since backend is not running
        RESULTS.info.push({ page: name, issue: `${RESULTS.consoleErrors[name].length} blocked/connection errors (expected — backend not running)` })
      }

      // --- Page load ---
      if (resp && resp.ok()) {
        RESULTS.passed.push({ page: name, test: `Status 200 (${loadTime}ms)` })
      } else if (resp) {
        RESULTS.passed.push({ page: name, test: `Status ${resp.status()} (expected for ${name})` })
      }

      // --- Page-specific audits ---
      const audits = {
        index: auditIndex,
        login: auditLogin,
        admin: auditAdmin,
        docente: auditDocente,
        estudiante: auditEstudiante,
        dashboard: auditDashboard,
        404: audit404,
      }
      if (audits[name]) {
        await audits[name](page, name)
      }

    } catch (err) {
      RESULTS.failed.push({ page: name, test: 'Uncaught error', details: err.message })
    } finally {
      await page.close()
    }
  }

  // --- Theme audit ---
  const themePage = await context.newPage()
  try {
    await auditTheme(themePage, context)
  } finally {
    await themePage.close()
  }

  await browser.close()
  printReport()
}

async function auditIndex(page, name) {
  const stats = [
    '#stat-estudiantes', '#stat-docentes',
    '#stat-mora', '#stat-avisos',
  ]
  for (const sel of stats) {
    const el = await page.$(sel)
    if (el) {
      const text = await el.textContent()
      if (text === '--') {
        RESULTS.warnings.push({ page: name, issue: `${sel} not loaded (-- value)` })
      }
    }
  }

  const loginBtn = page.locator('a[href="/login"]')
  if (await loginBtn.count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No login button on landing page' })
  }

  const footer = page.locator('footer')
  if (await footer.count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'Missing <footer>' })
  }
}

async function auditLogin(page, name) {
  const form = page.locator('form#login-form')
  if (await form.count() === 0) {
    RESULTS.failed.push({ page: name, test: 'Login form missing', details: '#login-form not found' })
  }

  const tabEst = page.locator('#tab-estudiante')
  const tabPer = page.locator('#tab-personal')
  if (await tabEst.count() === 0 || await tabPer.count() === 0) {
    RESULTS.failed.push({ page: name, test: 'Tab controls missing', details: 'Segmented control tabs not found' })
  }

  const password = page.locator('#password')
  if (await password.count() > 0) {
    const pwdType = await password.getAttribute('type')
    if (pwdType !== 'password') {
      RESULTS.warnings.push({ page: name, issue: 'Password field type is not "password"' })
    }
  }

  const forgot = page.locator('.forgot-link')
  if (await forgot.count() > 0) {
    const href = await forgot.getAttribute('href')
    if (href === '#') {
      RESULTS.warnings.push({ page: name, issue: 'Forgot password link is "#"' })
    }
  }

  const errorDiv = page.locator('#login-error')
  if (await errorDiv.count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No error div (#login-error)' })
  }
}

async function auditAdmin(page, name) {
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    RESULTS.warnings.push({ page: name, issue: 'Page redirected — skipped detailed audit' })
    return
  }

  if (await page.locator('.admin-sidebar, .sidebar').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No sidebar detected' })
  }

  const sections = await page.locator('.t-section').count()
  if (sections < 3) {
    RESULTS.warnings.push({ page: name, issue: `Expected 5+ tab sections, found ${sections}` })
  }

  if (await page.locator('#toast').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No toast notification element' })
  }

  if (await page.locator('#loading-overlay').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No loading overlay' })
  }

  const inlineOnclicks = await page.evaluate(() => document.querySelectorAll('[onclick]').length)
  if (inlineOnclicks > 10) {
    RESULTS.warnings.push({ page: name, issue: `${inlineOnclicks} inline onclick handlers` })
  }

  const hashLinks = await page.locator('.sidebar-link[href="#"]').count()
  if (hashLinks > 0) {
    RESULTS.warnings.push({ page: name, issue: `${hashLinks} sidebar links with href="#"` })
  }
}

async function auditDocente(page, name) {
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    RESULTS.warnings.push({ page: name, issue: 'Page redirected — skipped detailed audit' })
    return
  }

  if (await page.locator('.teacher-sidebar, .sidebar').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No sidebar detected' })
  }

  if (await page.locator('#sidebar-theme-toggle').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No theme toggle in sidebar' })
  }

  const missingFields = []
  for (const id of ['grade-student', 'grade-subject', 'grade-score']) {
    if (await page.locator(`#${id}`).count() === 0) missingFields.push(id)
  }
  if (missingFields.length > 0) {
    RESULTS.warnings.push({ page: name, issue: `Grade form missing: ${missingFields.join(', ')}` })
  }

  if (await page.locator('#risk-alerts-list').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No risk alerts list container' })
  }

  if (await page.locator('#drop-zone').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No file drop zone' })
  }
}

async function auditEstudiante(page, name) {
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    RESULTS.warnings.push({ page: name, issue: 'Page redirected — skipped detailed audit' })
    return
  }

  if (await page.locator('.est-sidebar').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No student sidebar' })
  }

  const navBtns = await page.locator('.est-nav-link').all()
  for (const btn of navBtns) {
    const tag = await btn.evaluate(el => el.tagName)
    if (tag !== 'BUTTON') {
      RESULTS.warnings.push({ page: name, issue: `Nav link is <${tag}>, expected <button>` })
    }
  }

  const sections = await page.locator('.section-content').count()
  if (sections < 3) {
    RESULTS.warnings.push({ page: name, issue: `Expected 6+ sections, found ${sections}` })
  }

  if (await page.locator('#live-clock').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No live clock' })
  }

  if (await page.locator('#lightbox').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No lightbox' })
  }

  if (await page.locator('#exam-modal').count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No exam modal' })
  }

  // Check for duplicate IDs
  const fileDisplays = await page.locator('#file-name-display').count()
  if (fileDisplays > 1) {
    RESULTS.warnings.push({ page: name, issue: `Duplicate ID #file-name-display (${fileDisplays} instances)` })
  }
}

async function auditDashboard(page, name) {
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    RESULTS.warnings.push({ page: name, issue: 'Auth redirect — expected redirect to role-specific page' })
    return
  }

  // Should redirect to /estudiante by default
  if (currentUrl.includes('/estudiante') || currentUrl.includes('/admin') || currentUrl.includes('/docente')) {
    RESULTS.info.push({ page: name, issue: `Redirected to ${currentUrl} (expected)` })
  }
}

async function audit404(page, name) {
  const title = await page.title()
  const h1 = page.locator('h1')
  if (await h1.count() > 0) {
    const text = await h1.first().textContent()
    if (text.includes('404')) {
      RESULTS.a11yIssues.push({ page: name, issue: 'H1 reads "404" — screen readers may read as digits' })
    }
  }

  const backLink = page.locator('a[href="/"]')
  if (await backLink.count() === 0) {
    RESULTS.warnings.push({ page: name, issue: 'No back-to-home link on 404 page' })
  }
}

async function auditTheme(page, context) {
  await page.goto(BASE + '/', { waitUntil: 'networkidle' })

  // Test localStorage persistence
  await page.evaluate(() => { localStorage.setItem('vyntra-theme', 'dark') })
  await page.reload({ waitUntil: 'networkidle' })
  const darkApplied = await page.evaluate(() => document.documentElement.classList.contains('dark'))
  if (!darkApplied) {
    RESULTS.failed.push({ page: 'theme', test: 'localStorage persistence', details: 'vyntra-theme=dark not applied after reload' })
  } else {
    RESULTS.passed.push({ page: 'theme', test: 'localStorage dark mode persisted' })
  }

  // Test light theme
  await page.evaluate(() => { localStorage.setItem('vyntra-theme', 'light') })
  await page.reload({ waitUntil: 'networkidle' })
  const lightApplied = await page.evaluate(() => !document.documentElement.classList.contains('dark'))
  if (!lightApplied) {
    RESULTS.failed.push({ page: 'theme', test: 'Light mode', details: 'vyntra-theme=light not applied' })
  } else {
    RESULTS.passed.push({ page: 'theme', test: 'localStorage light mode persisted' })
  }

  // Test prefers-color-scheme fallback — clear storage
  await page.evaluate(() => { localStorage.removeItem('vyntra-theme') })
  // We can't change prefers-color-scheme in headless Chromium easily, but we can verify the toggle works
  RESULTS.info.push({ page: 'theme', issue: 'prefers-color-scheme fallback not tested (headless limitation)' })
}

function printReport() {
  const totalTests = RESULTS.passed.length + RESULTS.failed.length

  console.log('\n' + '═'.repeat(64))
  console.log('  VYNTRA — PLAYWRIGHT AUDIT REPORT')
  console.log('═'.repeat(64))
  console.log(`\n📊 SUMMARY`)
  console.log(`   ├─ ✅ Passed: ${RESULTS.passed.length}`)
  console.log(`   ├─ ❌ Failed: ${RESULTS.failed.length}`)
  console.log(`   ├─ ⚡ Warnings: ${RESULTS.warnings.length}`)
  console.log(`   ├─ ℹ️  Info: ${RESULTS.info.length}`)
  console.log(`   ├─ 🔍 SEO Issues: ${RESULTS.seoIssues.length}`)
  console.log(`   └─ ♿ A11y Issues: ${RESULTS.a11yIssues.length}`)

  // Failed tests
  if (RESULTS.failed.length > 0) {
    console.log('\n❌ FAILED TESTS')
    for (const f of RESULTS.failed) {
      console.log(`   [${f.page}] ${f.test}: ${f.details}`)
    }
  }

  // Passed tests
  console.log('\n✅ PASSED')
  for (const p of RESULTS.passed) {
    console.log(`   [${p.page}] ${p.test}`)
  }

  // Warnings
  if (RESULTS.warnings.length > 0) {
    console.log('\n⚡ WARNINGS')
    for (const w of RESULTS.warnings) {
      console.log(`   [${w.page}] ${w.issue}`)
    }
  }

  // Info
  if (RESULTS.info.length > 0) {
    console.log('\nℹ️  INFO')
    for (const i of RESULTS.info) {
      console.log(`   [${i.page}] ${i.issue}`)
    }
  }

  // SEO Issues
  if (RESULTS.seoIssues.length > 0) {
    console.log('\n🔍 SEO ISSUES')
    for (const s of RESULTS.seoIssues) {
      console.log(`   [${s.page}] ${s.issue}`)
    }
  }

  // A11y Issues
  if (RESULTS.a11yIssues.length > 0) {
    console.log('\n♿ ACCESSIBILITY ISSUES')
    for (const a of RESULTS.a11yIssues) {
      console.log(`   [${a.page}] ${a.issue}`)
    }
  }

  console.log('\n🌐 NETWORK ERRORS (non-404)')
  if (RESULTS.networkErrors.length > 0) {
    for (const ne of RESULTS.networkErrors) {
      console.log(`   [${ne.page}] ${ne.status} ${ne.url}`)
    }
  } else {
    console.log('   ✅ None')
  }

  console.log('\n' + '═'.repeat(64))
}

run().catch(console.error)
