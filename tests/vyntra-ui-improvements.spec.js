// @ts-check
import { test, expect } from '@playwright/test';

test.describe('Vyntra UI Improvements', () => {
  // Test para verificar la navegación responsive en dispositivos móviles
  test('debería funcionar correctamente en dispositivos móviles', async ({ page }) => {
    // Configurar viewport móvil
    await page.setViewportSize({ width: 375, height: 667 });
    
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
  
  // Test para verificar la navegación entre secciones
  test('debería permitir la navegación entre secciones del dashboard', async ({ page }) => {
    // Navegar a la página de login
    await page.goto('/login');
    
    // Completar el formulario de login como estudiante
    await page.fill('#doc-id', 'EST-001');
    await page.fill('#password', 'password123');
    
    // Enviar el formulario
    await page.click('#login-submit');
    
    // Esperar a que se redirija al dashboard
    await page.waitForURL('**/estudiante');
    
    // Verificar que el dashboard se carga correctamente
    await expect(page).toHaveTitle(/VYNTRA · Estudiante/);
    
    // Navegar a la sección de notas
    await page.click('text=Notas');
    
    // Verificar que la sección de notas se carga
    await expect(page.locator('text=Control de Notas')).toBeVisible();
    
    // Volver al dashboard principal
    await page.click('text=Dashboard');
    
    // Verificar que el dashboard principal se muestra
    await expect(page.locator('.welcome-banner h1')).toBeVisible();
  });
});
</content>