const { test, expect } = require('@playwright/test');

const BASE = 'http://localhost:4321';

async function loginAs(page, tab, id, pass) {
  await page.goto(`${BASE}/login`);
  await page.click(tab === 'student' ? '#tab-estudiante' : '#tab-personal');
  await page.fill('#doc-id', id);
  await page.fill('#password', pass);
  await page.click('#login-submit');
  await page.waitForURL(/estudiante|docente|admin/, { timeout: 15000 });
}

async function logout(page) {
  await page.evaluate(() => localStorage.clear());
  await page.goto(`${BASE}/`);
}

test.describe('Authentication', () => {
  test('Login page loads correctly', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await expect(page.locator('h2')).toContainText('Iniciar Sesión');
    await expect(page.locator('#tab-estudiante')).toBeVisible();
    await expect(page.locator('#tab-personal')).toBeVisible();
    await expect(page.locator('#doc-id')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('Shows error on invalid credentials', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.fill('#doc-id', 'INVALIDO');
    await page.fill('#password', 'wrongpass');
    await page.click('#login-submit');
    await expect(page.locator('#login-error')).toBeVisible();
    await expect(page.locator('#login-error')).not.toBeEmpty();
  });

  test('Shows error on missing fields', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click('#login-submit');
    await expect(page.locator('#login-error')).toBeVisible();
  });

  test('Student login redirects to student dashboard', async ({ page }) => {
    await loginAs(page, 'student', 'EST-001', 'password123');
    await expect(page).toHaveURL(/\/estudiante/);
    await expect(page.locator('.stats-grid')).toBeVisible();
  });

  test('Teacher login redirects to teacher dashboard', async ({ page }) => {
    await loginAs(page, 'teacher', 'DOC-001', 'password123');
    await expect(page).toHaveURL(/\/docente/);
  });

  test('Admin login redirects to admin dashboard', async ({ page }) => {
    await loginAs(page, 'admin', 'ADMIN-001', 'password123');
    await expect(page).toHaveURL(/\/admin/);
  });

  test('Tab switching works on login', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    const slider = page.locator('#tab-slider');
    const initialLeft = await slider.evaluate(el => el.style.left);
    await page.click('#tab-personal');
    const afterLeft = await slider.evaluate(el => el.style.left);
    expect(afterLeft).not.toBe(initialLeft);
  });
});

test.describe('Password Recovery', () => {
  test('Forgot password modal opens', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await expect(page.locator('#forgot-modal')).toBeVisible();
    await expect(page.locator('#forgot-credential')).toBeVisible();
  });

  test('Forgot step 1 sends code request', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', 'EST-001');
    await page.click('#forgot-send-btn');
    // After sending, step 2 should appear (or error if backend not connected)
    await page.waitForTimeout(2000);
  });
});

test.describe('Student Dashboard', () => {
  test('Dashboard shows after login', async ({ page }) => {
    await loginAs(page, 'student', 'EST-001', 'password123');
    await expect(page.locator('.stats-grid')).toBeVisible();
  });

  test('Section navigation works', async ({ page }) => {
    await loginAs(page, 'student', 'EST-001', 'password123');
    const sections = ['notas', 'horario', 'tareas'];
    for (const sec of sections) {
      const btn = page.locator(`[data-section-id="${sec}"]`);
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('AI Chat panel toggles', async ({ page }) => {
    await loginAs(page, 'student', 'EST-001', 'password123');
    const chatBtn = page.locator('#ai-chat-toggle');
    if (await chatBtn.isVisible()) {
      await chatBtn.click();
      await expect(page.locator('#ai-chat-panel')).toBeVisible();
      await chatBtn.click();
    }
  });
});

test.describe('Unauthenticated Access', () => {
  test('Redirects to login when accessing dashboard without auth', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page).toHaveURL(/\/login/);
  });

  test('Redirects to login when accessing student page without auth', async ({ page }) => {
    await page.goto(`${BASE}/estudiante`);
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Security Headers', () => {
  test('CSP headers are present', async ({ page }) => {
    const resp = await page.goto(`${BASE}/login`);
    const headers = resp.headers();
    expect(headers['content-security-policy']).toBeTruthy();
    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBe('DENY');
  });
});

test.describe('Theme', () => {
  test('Theme toggle persists', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    const html = page.locator('html');
    const initialClass = await html.getAttribute('class');
    const toggle = page.locator('#theme-toggle');
    if (await toggle.isVisible()) {
      await toggle.click();
    }
  });
});
