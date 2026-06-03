import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const FRONTEND_URL = 'http://localhost:4321';
const BACKEND_URL = 'http://localhost:8000';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.resolve(__dirname, '..', 'monitor-screenshots');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const CREDENTIALS = [
  { role: 'admin',   tab: 'personal',   id: '1',   pass: 'admin',  dashboard: '/admin' },
  { role: 'teacher', tab: 'personal',   id: '11',  pass: 'profe',  dashboard: '/docente' },
  { role: 'student', tab: 'estudiante', id: '101', pass: 'alumno', dashboard: '/estudiante' },
];

let cycle = 0;
let browser;

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function checkHealth() {
  const start = Date.now();
  try {
    const res = await fetch(`${BACKEND_URL}/api/health`, { signal: AbortSignal.timeout(5000) });
    const ok = res.ok;
    const latency = Date.now() - start;
    let body = null;
    try { body = await res.text(); } catch (e) {}
    return { ok, status: res.status, latency, body };
  } catch (err) {
    return { ok: false, status: 0, latency: Date.now() - start, error: err.message };
  }
}

async function tryHealth() {
  const result = await checkHealth();
  return result.ok
    ? `✅ OK (${result.latency}ms)`
    : `❌ FAIL (${result.status} / ${result.error || 'timeout'})`;
}

async function tryGoto(page, url, label) {
  const errors = [];
  const requests = [];

  const onReqFail = (req) => {
    if (req.url().includes('localhost') || req.url().includes('4321') || req.url().includes('8000') || req.url().includes('10000')) {
      requests.push({ url: req.url().slice(0, 80), status: 'FAILED', error: req.failure()?.errorText });
    }
  };
  const onPageErr = (err) => { errors.push(err.message); };
  const onReq = (req) => { requests.push({ url: req.url().slice(0, 80), status: 'REQUEST' }); };
  const onResp = (resp) => {
    if (resp.status() >= 400) {
      requests.push({ url: resp.url().slice(0, 80), status: resp.status() });
    }
  };

  page.on('pageerror', onPageErr);
  page.on('requestfailed', onReqFail);
  page.on('response', onResp);

  const start = Date.now();
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  } catch (err) {
    page.removeListener('pageerror', onPageErr);
    page.removeListener('requestfailed', onReqFail);
    page.removeListener('response', onResp);
    return { ok: false, loadTime: Date.now() - start, errors: [err.message], failedRequests: [] };
  }
  const loadTime = Date.now() - start;

  page.removeListener('pageerror', onPageErr);
  page.removeListener('requestfailed', onReqFail);
  page.removeListener('response', onResp);

  const failedRequests = requests.filter(r => r.status === 'FAILED' || (typeof r.status === 'number' && r.status >= 400));

  return { ok: errors.length === 0 && failedRequests.length === 0, loadTime, errors, failedRequests };
}

async function checkPage(page, url, label) {
  const result = await tryGoto(page, url, label);
  if (result.ok) {
    return `✅ ${label}: ${result.loadTime}ms`;
  } else {
    let details = '';
    if (result.errors.length) details += ` errors:[${result.errors.join('; ').slice(0, 120)}]`;
    if (result.failedRequests.length) details += ` failed:[${result.failedRequests.map(r => `${r.status} ${r.url}`).join('; ').slice(0, 120)}]`;
    return `❌ ${label}: ${result.loadTime}ms${details}`;
  }
}

async function takeScreenshot(page, name) {
  const filename = `cycle-${String(cycle).padStart(3, '0')}-${name}.png`;
  const filepath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: false });
  return filename;
}

async function loginAndCheck(page, cred) {
  const errors = [];
  const onPageErr = (err) => errors.push(err.message);
  page.on('pageerror', onPageErr);

  try {
    await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 });
  } catch (err) {
    page.removeListener('pageerror', onPageErr);
    return { ok: false, error: `Login page load failed: ${err.message}` };
  }

  await page.waitForTimeout(500);

  if (cred.tab === 'personal') {
    await page.click('#tab-personal');
    await page.waitForTimeout(300);
  }

  await page.fill('#doc-id', cred.id);
  await page.fill('#password', cred.pass);
  await page.click('#login-submit');

  try {
    await page.waitForURL(`**${cred.dashboard}`, { timeout: 10000 });
  } catch (err) {
    page.removeListener('pageerror', onPageErr);
    return { ok: false, error: `Redirect to ${cred.dashboard} failed: ${err.message}` };
  }

  await page.waitForTimeout(1000);

  const title = await page.title();
  const failedReqs = [];
  page.on('response', (resp) => {
    if (resp.status() >= 400) failedReqs.push(`${resp.status()} ${resp.url().slice(0, 60)}`);
  });

  page.removeListener('pageerror', onPageErr);

  return {
    ok: errors.length === 0,
    title,
    errors,
    failedRequests: failedReqs,
  };
}

async function runCycle(context) {
  cycle++;
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => pageErrors.push(err.message));

  const lines = [];
  lines.push(`─── CICLO #${cycle} ─── [${new Date().toLocaleTimeString()}]`);

  // 1. Health check
  const healthResult = await checkHealth();
  lines.push(`  API Health: ${healthResult.ok ? '✅' : '❌'} (${healthResult.latency}ms, status ${healthResult.status})`);

  // 2. Landing page
  const landingResult = await checkPage(page, FRONTEND_URL, 'Landing');
  lines.push(`  ${landingResult}`);
  if (landingResult.includes('✅')) {
    const fname = await takeScreenshot(page, 'landing');
    lines.push(`    📸 screenshot: ${fname}`);
  }

  // 3. Login page
  const loginPageResult = await checkPage(page, `${FRONTEND_URL}/login`, 'Login page');
  lines.push(`  ${loginPageResult}`);

  // 4. Try each role login
  for (const cred of CREDENTIALS) {
    const loginResult = await loginAndCheck(page, cred);
    if (loginResult.ok) {
      lines.push(`  ✅ ${cred.role} login -> ${cred.dashboard} (title: "${loginResult.title}")`);
      const fname = await takeScreenshot(page, `dashboard-${cred.role}`);
      lines.push(`    📸 screenshot: ${fname}`);
      if (loginResult.errors.length) {
        lines.push(`    ⚠️  page errors: ${loginResult.errors.join('; ').slice(0, 100)}`);
      }
    } else {
      lines.push(`  ❌ ${cred.role} login: ${loginResult.error}`);
    }
  }

  // 5. Console errors summary
  if (consoleErrors.length) {
    lines.push(`  ⚠️  Console errors (${consoleErrors.length}):`);
    consoleErrors.slice(0, 5).forEach(e => lines.push(`      - ${e.slice(0, 120)}`));
  }
  if (pageErrors.length) {
    lines.push(`  ⚠️  Page errors (${pageErrors.length}):`);
    pageErrors.slice(0, 5).forEach(e => lines.push(`      - ${e.slice(0, 120)}`));
  }

  const summary = lines.join('\n');
  console.log(summary);
  console.log('');

  await page.close();
  return { consoleErrors, pageErrors, healthResult };
}

async function main() {
  console.log('═══════════════════════════════════════════');
  console.log('  VYNTRA MONITOR — Playwright Observer');
  console.log(`  Frontend: ${FRONTEND_URL}`);
  console.log(`  Backend:  ${BACKEND_URL}`);
  console.log(`  Screenshots: ${SCREENSHOT_DIR}`);
  console.log('═══════════════════════════════════════════');
  console.log('');

  browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  });

  try {
    while (true) {
      const result = await runCycle(context);

      if (result.healthResult.ok && result.consoleErrors.length === 0 && result.pageErrors.length === 0) {
        console.log(`  ✅ Todo OK. Próximo ciclo en 15s...`);
      } else {
        console.log(`  ⚠️  Se detectaron issues. Próximo ciclo en 15s...`);
      }
      console.log('');

      await sleep(15000);
    }
  } finally {
    await browser.close();
  }
}

main().catch(err => {
  console.error('MONITOR CRASHED:', err);
  process.exit(1);
});
