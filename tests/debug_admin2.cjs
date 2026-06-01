const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Simulate what the audit does
  page.on('console', msg => { if (msg.type() === 'error') console.log('CONSOLE ERROR:', msg.text()); });
  page.on('pageerror', err => console.log('PAGE_ERROR:', err.message));
  page.on('response', r => { if (r.status() >= 400) console.log(`  NET ${r.status()}: ${r.url().slice(0,80)}`); });

  // Step 1: set auth
  await page.goto('http://localhost:4321/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('access_token', 'test_token');
    localStorage.setItem('userId', 'admin001');
    localStorage.setItem('profile_id', 'admin001');
    localStorage.setItem('userRole', 'admin');
    localStorage.setItem('userName', 'Admin Test');
  });

  // Verify localStorage was set
  const role = await page.evaluate(() => localStorage.getItem('userRole'));
  console.log('localStorage role after set:', role);

  // Step 2: navigate to admin
  const resp = await page.goto('http://localhost:4321/admin', { waitUntil: 'networkidle', timeout: 10000 });
  console.log('Response status:', resp ? resp.status() : 'null');
  console.log('Final URL:', page.url());

  // Check what page we're on
  const isAdmin = page.url().includes('/admin');
  console.log('On admin page:', isAdmin);

  // Check elements
  const sidebar = await page.$('.admin-sidebar');
  console.log('admin-sidebar found:', !!sidebar);

  const sections = await page.$$('.t-section');
  console.log('t-sections:', sections.length);

  const toast = await page.$('#toast');
  console.log('#toast found:', !!toast);

  const loading = await page.$('#loading-overlay');
  console.log('#loading-overlay found:', !!loading);

  // Check role at actual page load
  const roleAtLoad = await page.evaluate(() => localStorage.getItem('userRole'));
  console.log('localStorage role at admin load:', roleAtLoad);

  const title = await page.title();
  console.log('Page title:', title);

  await browser.close();
})();
