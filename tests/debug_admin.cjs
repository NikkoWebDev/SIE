const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://localhost:4321/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem('access_token', 'test');
    localStorage.setItem('userId', 'admin001');
    localStorage.setItem('userRole', 'admin');
    localStorage.setItem('userName', 'Admin Test');
  });
  await page.goto('http://localhost:4321/admin', { waitUntil: 'networkidle', timeout: 10000 });
  console.log('URL:', page.url());
  console.log('Title:', await page.title());

  const sel = 'aside';
  const sidebars = await page.$$(sel);
  console.log('Aside elements:', sidebars.length);

  const adminSidebar = await page.$('.admin-sidebar');
  console.log('admin-sidebar class:', !!adminSidebar);

  const sidebarClass = await page.$('.sidebar');
  console.log('sidebar class:', !!sidebarClass);

  const bodyHTML = await page.evaluate(() => document.body.innerHTML.length);
  console.log('Body HTML length:', bodyHTML);

  const classes = await page.evaluate(() => document.body.className);
  console.log('Body classes:', classes);

  console.log('\nFirst 500 chars of body:');
  const first500 = await page.evaluate(() => document.body.innerHTML.slice(0, 500));
  console.log(first500);

  await browser.close();
})();
