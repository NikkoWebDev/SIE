import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '*.spec.js',
  timeout: 30000,
  retries: 1,
  use: {
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        headless: false
      }
    },
    {
      name: 'ci',
      use: {
        browserName: 'chromium',
        headless: true
      }
    }
  ]
});
