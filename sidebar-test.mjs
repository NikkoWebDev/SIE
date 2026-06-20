import { chromium } from 'playwright';
const BASE = 'http://localhost:4321';
const browser = await chromium.launch({ headless: true });

async function captureDashboard(role, url, localStorageData) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  // Intercept ALL API calls to return mock data
  await page.route('**/api/**', route => {
    const reqUrl = route.request().url();
    const method = route.request().method();

    // Auth verify
    if (reqUrl.includes('/api/auth/verify')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    // Grades
    if (reqUrl.includes('/api/grades')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    // Notices
    if (reqUrl.includes('/api/notices')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: [], total: 0 }) });
    }
    // Risk
    if (reqUrl.includes('/api/students/risk')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    // Admin stats
    if (reqUrl.includes('/api/admin/stats')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total_students: 150, total_teachers: 12, total_admins: 3, total_grades: 500, promedio_general: 4.2, mora: 5, total_notices: 8, total_exams: 15 }) });
    }
    // Exams
    if (reqUrl.includes('/api/exams') || reqUrl.includes('/api/student/exams')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    // Candidates
    if (reqUrl.includes('/api/admin/candidates')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    // Admin students
    if (reqUrl.includes('/api/admin/students')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: [], total: 0 }) });
    }
    // Admin teachers
    if (reqUrl.includes('/api/admin/teachers') || reqUrl.includes('/api/admin/assign-teacher')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ data: [], total: 0 }) });
    }
    // Subjects
    if (reqUrl.includes('/api/subjects') || reqUrl.includes('/api/admin/subjects')) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    // Default: empty JSON
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Go to login first to set localStorage
  await page.goto(BASE + '/login', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(500);

  // Inject session data
  await page.evaluate((data) => {
    for (const [k, v] of Object.entries(data)) localStorage.setItem(k, v);
  }, localStorageData);

  // Navigate to dashboard
  await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // Full page screenshot
  await page.screenshot({ path: `/tmp/dash-${role}.png`, fullPage: true });

  // Sidebar info
  const sidebarVisible = await page.locator('[id^="vyntra-sidebar-"]').first().isVisible().catch(() => false);
  const sidebarButtons = await page.locator('[data-section-id]').count();
  const sidebarLabels = await page.locator('[data-section-id]').allTextContents();
  const topbarHeading = await page.locator('.topbar-heading').textContent().catch(() => 'N/A');
  const topbarSubtitle = await page.locator('.topbar-subtitle').textContent().catch(() => 'N/A');
  const sections = await page.locator('[id^="sec-"]').count();
  const noiseCount = await page.locator('.noise-overlay').count();
  const sidebarUser = await page.locator('[id^="sidebar-username-"]').textContent().catch(() => 'N/A');

  console.log(`\n=== ${role.toUpperCase()} ===`);
  console.log(`URL: ${page.url()}`);
  console.log(`Sidebar visible: ${sidebarVisible}`);
  console.log(`Sidebar buttons: ${sidebarButtons}`);
  console.log(`Sidebar labels: ${sidebarLabels.join(', ')}`);
  console.log(`Sidebar username: ${sidebarUser}`);
  console.log(`Topbar heading: ${topbarHeading}`);
  console.log(`Topbar subtitle: ${topbarSubtitle}`);
  console.log(`Sections: ${sections}`);
  console.log(`Noise overlays: ${noiseCount}`);

  // Click each sidebar section and screenshot
  for (let i = 0; i < Math.min(sidebarButtons, 10); i++) {
    const btn = page.locator('[data-section-id]').nth(i);
    const sectionId = await btn.getAttribute('data-section-id');
    await btn.click().catch(() => {});
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `/tmp/dash-${role}-${sectionId}.png`, fullPage: true });
    const heading = await page.locator('.topbar-heading').textContent().catch(() => 'N/A');
    console.log(`  [${sectionId}] -> topbar="${heading}"`);
  }

  const uniqueErrors = [...new Set(consoleErrors.filter(e => !e.includes('ERR_CONNECTION_REFUSED')))];
  if (uniqueErrors.length > 0) console.log(`JS errors: ${uniqueErrors.join('; ')}`);

  await ctx.close();
  return { role, sidebarButtons, sidebarLabels, sections, noiseCount };
}

const studentSession = {
  'userRole': 'student', 'userId': '101', 'userName': 'Alumno Test',
  'profile_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'ws_access_token': 'dummy'
};
const teacherSession = {
  'userRole': 'teacher', 'userId': '11', 'userName': 'Profe Test',
  'profile_id': 'b2c3d4e5-f6a7-8901-bcde-f12345678901', 'ws_access_token': 'dummy'
};
const adminSession = {
  'userRole': 'admin', 'userId': '1', 'userName': 'Admin Test',
  'profile_id': 'c3d4e5f6-a7b8-9012-cdef-123456789012', 'ws_access_token': 'dummy'
};

await captureDashboard('student', '/estudiante', studentSession);
await captureDashboard('teacher', '/docente', teacherSession);
await captureDashboard('admin', '/admin', adminSession);

await browser.close();
console.log('\nDONE - all screenshots saved to /tmp/dash-*.png');
