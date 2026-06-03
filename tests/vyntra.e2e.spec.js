// @ts-check
import { test, expect } from '@playwright/test';

// URL base del servidor de desarrollo
const BASE_URL = 'http://localhost:4321';

// Configuración global para las pruebas
test.use({
  viewport: { width: 1920, height: 1080 },
  headless: false, // Ejecutar en modo visible para observar
});

test.describe('Vyntra Estudiante Dashboard', () => {
  test('debería cargar correctamente el dashboard de estudiante', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como estudiante
    await page.fill('#doc-id', 'EST-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/estudiante');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Estudiante/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('.welcome-banner h1')).toBeVisible();
    await expect(page.locator('.stats-grid')).toBeVisible();
  });
});

test.describe('Vyntra Docente Dashboard', () => {
  test('debería cargar correctamente el dashboard de docente', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como docente
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'DOC-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/docente');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Docente/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#teacher-sidebar')).toBeVisible();
    await expect(page.locator('#page-title')).toHaveText('Panel Docente');
  });
});

test.describe('Vyntra Admin Dashboard', () => {
  test('debería cargar correctamente el dashboard de administrador', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como administrador
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'ADMIN-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/admin');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Administración/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#admin-sidebar')).toBeVisible();
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });
});

test.describe('Vyntra Estudiante Dashboard', () => {
  test('debería cargar correctamente el dashboard de estudiante', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como estudiante
    await page.fill('#doc-id', 'EST-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/estudiante');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Estudiante/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('.welcome-banner h1')).toBeVisible();
    await expect(page.locator('.stats-grid')).toBeVisible();
  });
});

test.describe('Vyntra Docente Dashboard', () => {
  test('debería cargar correctamente el dashboard de docente', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como docente
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'DOC-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/docente');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Docente/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#teacher-sidebar')).toBeVisible();
    await expect(page.locator('#page-title')).toHaveText('Panel Docente');
  });
});

test.describe('Vyntra Admin Dashboard', () => {
  test('debería cargar correctamente el dashboard de administrador', async ({ page }) => {
    // Navegar a la página de login
    await page.goto(`${BASE_URL}/login`);
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como administrador
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'ADMIN-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/admin');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Administración/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#admin-sidebar')).toBeVisible();
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });
});

test.describe('Vyntra Estudiante Dashboard', () => {
  test('debería cargar correctamente el dashboard de estudiante', async ({ page }) => {
    // Navegar a la página de login
    await page.goto('/login');
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como estudiante
    await page.fill('#doc-id', 'EST-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/estudiante');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Estudiante/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('.welcome-banner h1')).toBeVisible();
    await expect(page.locator('.stats-grid')).toBeVisible();
  });
});

test.describe('Vyntra Docente Dashboard', () => {
  test('debería cargar correctamente el dashboard de docente', async ({ page }) => {
    // Navegar a la página de login
    await page.goto('/login');
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como docente
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'DOC-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/docente');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Docente/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#teacher-sidebar')).toBeVisible();
    await expect(page.locator('#page-title')).toHaveText('Panel Docente');
  });
});

test.describe('Vyntra Admin Dashboard', () => {
  test('debería cargar correctamente el dashboard de administrador', async ({ page }) => {
    // Navegar a la página de login
    await page.goto('/login');
    
    // Verificar que la página de login se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Acceso/);
    
    // Completar el formulario de login como administrador
    await page.click('#tab-personal');
    await page.fill('#doc-id', 'ADMIN-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/admin');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Administración/);
    
    // Verificar elementos clave del dashboard
    await expect(page.locator('#admin-sidebar')).toBeVisible();
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });
});