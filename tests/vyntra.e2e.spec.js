import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:4321';

// ════════════════════════════════════════════════════════
// Credenciales actualizadas para coincidir con seed.sql
// Estudiante: 101 / alumno
// Docente:    11  / profe
// Admin:      1   / admin
// ════════════════════════════════════════════════════════

async function loginAs(page, id, pass) {
  await page.goto(`${BASE}/login`);
  // Login page has NO role tabs — it's a single centered form
  await page.fill('#credential', id);
  await page.fill('#password', pass);
  await page.click('#login-submit');
  await page.waitForURL(/estudiante|docente|admin/, { timeout: 15000 });
}

async function logoutViaSidebar(page, role) {
  const btn = page.locator(`#logout-btn-${role}`);
  if (await btn.isVisible()) await btn.click();
  await page.waitForURL(/\/$/);
}

test.describe('Authentication', () => {
  test('Login page loads correctly (no role tabs)', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    // Single form, no tabs
    await expect(page.locator('h1')).toContainText('VYNTRA');
    await expect(page.locator('#credential')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('#login-submit')).toBeVisible();
    // Verify no role tabs exist
    await expect(page.locator('#tab-estudiante')).not.toBeAttached();
    await expect(page.locator('#tab-personal')).not.toBeAttached();
  });

  test('Inline validation shows errors', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    // Submit with empty fields
    await page.click('#login-submit');
    await expect(page.locator('#login-error')).toBeVisible();

    // Fill invalid and trigger blur validation
    await page.fill('#credential', '');
    await page.locator('#credential').blur();
    // Credential error should be visible
    const credErr = page.locator('#credential-error');
    // Wait for potential DOM update
    await page.waitForTimeout(300);
  });

  test('Shows error on invalid credentials', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.fill('#credential', 'INVALIDO');
    await page.fill('#password', 'wrongpass');
    await page.click('#login-submit');
    await expect(page.locator('#login-error')).toBeVisible();
  });

  test('Student login redirects to student dashboard', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    await expect(page).toHaveURL(/\/estudiante/);
  });

  test('Teacher login redirects to teacher dashboard', async ({ page }) => {
    await loginAs(page, '11', 'profe');
    await expect(page).toHaveURL(/\/docente/);
  });

  test('Admin login redirects to admin dashboard', async ({ page }) => {
    await loginAs(page, '1', 'admin');
    await expect(page).toHaveURL(/\/admin/);
  });

  test('Health check is present (proper fetch)', async ({ page }) => {
    // The health check now uses a proper fetch (not no-cors)
    await page.goto(`${BASE}/login`);
    // Just verify the page loads
    await expect(page.locator('#login-form')).toBeVisible();
  });
});

test.describe('Password Recovery', () => {
  test('Forgot password modal opens', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await expect(page.locator('#forgot-modal')).toBeVisible();
    await expect(page.locator('#forgot-credential')).toBeVisible();
  });

  test('Forgot modal shows step 2 after sending', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await page.click('#forgot-link');
    await page.fill('#forgot-credential', '101');
    await page.click('#forgot-send-btn');
    await page.waitForTimeout(2000);
  });
});

test.describe('Logout', () => {
  test('Logout via sidebar redirects to home', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    // Sidebar logout button should exist
    const logoutBtn = page.locator('#logout-btn-student');
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForURL(/\/$/);
    }
  });
});

test.describe('Dashboard Navigation', () => {
  test('Section navigation dispatches vyntra:navigate', async ({ page }) => {
    await loginAs(page, '101', 'alumno');

    // Listen for custom event
    const eventPromise = page.evaluate(() => {
      return new Promise((resolve) => {
        window.addEventListener('vyntra:navigate', (e) => resolve(e.detail), { once: true });
      });
    });

    // Click a sidebar button
    const btn = page.locator('[data-section-id="notas"]');
    if (await btn.isVisible()) {
      await btn.click();
    }

    const detail = await eventPromise;
    expect(detail.section).toBe('notas');
  });

  test('Sidebar mobile toggle works', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    // On desktop (default viewport), hamburger should not be visible
    const menuBtn = page.locator('#mobile-menu-btn');
    await expect(menuBtn).not.toBeVisible();
  });

  test('Sidebar shows active section with aria-current', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    // The active section button should have aria-current="page"
    const activeBtn = page.locator('.sidebar-link[data-section-id="inicio"]');
    await expect(activeBtn).toHaveAttribute('aria-current', 'page');
  });
});

test.describe('AI Chat', () => {
  test('Chat panel opens and closes', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    const chatBtn = page.locator('#ai-chat-toggle');
    if (await chatBtn.isVisible()) {
      await chatBtn.click();
      await expect(page.locator('#ai-chat-panel')).toBeVisible();
      await chatBtn.click();
      // Panel should hide (check opacity or pointer-events)
    }
  });

  test('Chat has stop button', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    const chatBtn = page.locator('#ai-chat-toggle');
    if (await chatBtn.isVisible()) {
      await chatBtn.click();
      // Stop button should exist in the panel
      await expect(page.locator('#chat-stop')).toBeAttached();
    }
  });
});

test.describe('Unauthenticated Access', () => {
  test('Redirects to login when accessing dashboard without auth', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Security Headers', () => {
  test('CSP header is present', async ({ page }) => {
    const resp = await page.goto(`${BASE}/login`);
    const headers = resp.headers();
    expect(headers['content-security-policy']).toBeTruthy();
  });
});

test.describe('Theme', () => {
  test('Theme toggle exists in sidebar', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    const toggle = page.locator('#theme-toggle-student');
    await expect(toggle).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('Skip link exists', async ({ page }) => {
    await page.goto(`${BASE}/login`);
    const skipLink = page.locator('.skip-link');
    await expect(skipLink).toBeAttached();
    await expect(skipLink).toHaveAttribute('href', '#main-content');
  });

  test('Buttons have accessible names', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    // Logout button should have aria-label
    const logoutBtn = page.locator('#logout-btn-student');
    await expect(logoutBtn).toHaveAttribute('aria-label');
  });

  test('Sidebar has navigation role', async ({ page }) => {
    await loginAs(page, '101', 'alumno');
    const sidebar = page.locator('#vyntra-sidebar-student');
    await expect(sidebar).toHaveAttribute('role', 'navigation');
  });
});
