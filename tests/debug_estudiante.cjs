const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Set auth
  await page.goto('http://localhost:4321/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('access_token', 'test');
    localStorage.setItem('userId', 'test123');
    localStorage.setItem('profile_id', 'test123');
    localStorage.setItem('userRole', 'estudiante');
    localStorage.setItem('userName', 'Test Student');
    localStorage.setItem('userGrade', '10°');
  });

  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', err => { errors.push('PAGE_ERROR: ' + err.message); });

  await page.goto('http://localhost:4321/estudiante', { waitUntil: 'load', timeout: 15000 });

  console.log('URL:', page.url());
  console.log('Title:', await page.title());

  const sidebar = await page.$('.est-sidebar');
  console.log('Sidebar exists:', !!sidebar);

  const name = await page.$('#student-name');
  console.log('Student name element:', !!name, name ? await (await name.textContent()).trim() : 'N/A');

  // Check all h1s excluding Astro toolbar ones
  const allH1s = await page.evaluate(() => {
    const els = document.querySelectorAll('h1');
    return Array.from(els).map(e => ({
      text: e.textContent.trim().slice(0, 60),
      visible: e.offsetParent !== null,
      id: e.id || '(none)',
      classes: e.className
    }));
  });
  console.log('H1 elements:', JSON.stringify(allH1s, null, 2));

  // Check if loadGrades exists in window
  const hasLoadGrades = await page.evaluate(() => typeof loadGrades !== 'undefined');
  console.log('loadGrades global:', hasLoadGrades);

  // Check for any key functions
  const keyFns = await page.evaluate(() => {
    const names = ['loadGrades', 'loadNotices', 'loadExams', 'loadCandidates', 'loadSubjects', 'init'];
    return names.map(n => ({ name: n, exists: eval('typeof ' + n) !== 'undefined' }));
  });
  console.log('Key functions:', JSON.stringify(keyFns, null, 2));

  // Screenshot
  await page.screenshot({ path: '/tmp/estudiante.png', fullPage: true });
  console.log('Screenshot saved');

  console.log('\nErrors (' + errors.length + '):');
  for (const e of errors) console.log('  ', e.slice(0, 250));

  await browser.close();
})();
