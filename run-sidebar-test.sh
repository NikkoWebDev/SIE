#!/bin/bash
set -e
cd /home/niko/Proyectos/C_sol/Vyntra

# Kill any existing serve
pkill -f "serve dist" 2>/dev/null || true
sleep 1

# Start serve WITHOUT -s (no SPA mode)
npx serve dist -p 4321 &
SERVER_PID=$!
sleep 4

# Verify server
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4321/login)
echo "Login page HTTP: $HTTP_CODE"

# Run Playwright
node -e "
import { chromium } from 'playwright';
const BASE = 'http://localhost:4321';
const browser = await chromium.launch({ headless: true });

async function loginAndCapture(role, id, password, url) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  await page.goto(BASE + '/login', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);

  await page.fill('#credential', id);
  await page.fill('#password', password);
  await page.click('#login-submit');
  await page.waitForTimeout(3000);

  await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  await page.screenshot({ path: '/tmp/dash-' + role + '.png', fullPage: true });

  const sidebarVisible = await page.locator('[id^=\"vyntra-sidebar-\"]').first().isVisible().catch(() => false);
  const sidebarButtons = await page.locator('[data-section-id]').count();
  const sidebarLabels = await page.locator('[data-section-id]').allTextContents();
  const topbarHeading = await page.locator('.topbar-heading').textContent().catch(() => 'N/A');
  const topbarSubtitle = await page.locator('.topbar-subtitle').textContent().catch(() => 'N/A');
  const sections = await page.locator('[id^=\"sec-\"]').count();
  const noiseCount = await page.locator('.noise-overlay').count();
  const sidebarUser = await page.locator('[id^=\"sidebar-username-\"]').textContent().catch(() => 'N/A');

  console.log('=== ' + role.toUpperCase() + ' ===');
  console.log('URL: ' + page.url());
  console.log('Sidebar visible: ' + sidebarVisible);
  console.log('Sidebar buttons: ' + sidebarButtons);
  console.log('Sidebar labels: ' + sidebarLabels.join(', '));
  console.log('Sidebar username: ' + sidebarUser);
  console.log('Topbar heading: ' + topbarHeading);
  console.log('Topbar subtitle: ' + topbarSubtitle);
  console.log('Sections: ' + sections);
  console.log('Noise overlays: ' + noiseCount);

  for (let i = 0; i < Math.min(sidebarButtons, 8); i++) {
    const btn = page.locator('[data-section-id]').nth(i);
    const sectionId = await btn.getAttribute('data-section-id');
    await btn.click().catch(() => {});
    await page.waitForTimeout(1500);
    await page.screenshot({ path: '/tmp/dash-' + role + '-' + sectionId + '.png', fullPage: true });
    const heading = await page.locator('.topbar-heading').textContent().catch(() => 'N/A');
    console.log('  Clicked [' + sectionId + '] -> topbar=\"' + heading + '\"');
  }

  if (consoleErrors.length > 0) console.log('Console errors: ' + consoleErrors.slice(0, 5).join('; '));
  await ctx.close();
}

(async () => {
  await loginAndCapture('student', '101', 'alumno', '/estudiante');
  await loginAndCapture('teacher', '11', 'profe', '/docente');
  await loginAndCapture('admin', '1', 'admin', '/admin');
  await browser.close();
  console.log('DONE');
})();
"

kill $SERVER_PID 2>/dev/null
