import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '*.spec.js',
  timeout: 30000,
  retries: 1,
  webServer: {
    command: 'python3 -m http.server 4321 --directory dist',
    port: 4321,
    reuseExistingServer: !process.env.CI,
    timeout: 15000,
  },
  use: {
    ignoreHTTPSErrors: true,
    video: 'on-first-retry',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        headless: false
      }
    },
    {
      name: 'ci',
      use: {
        ...devices['Desktop Chrome'],
        headless: true
      }
    },
    {
      name: 'mobile',
      use: {
        ...devices['iPhone 13'],
        headless: true
      }
    }
  ]
});
