const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const channel = process.env.CI ? undefined : 'chrome';
  const browser = await chromium.launch({ headless: true, ...(channel ? { channel } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const base = process.env.TEST_URL || 'http://127.0.0.1:3000';
    const visit = async path => {
      await page.goto(base + path);
      await page.locator('h1').waitFor();
      await page.waitForFunction(() => !document.body.innerText.includes('正在读取已验证的研究数据'));
    };
    await visit('/methodology/');
    await page.locator('#source-policy select').selectOption('corn');
    const china = page.locator('#source-policy tbody tr').filter({ has: page.locator('td:first-child', { hasText: /^中国$/ }) });
    assert((await china.innerText()).includes('CASDE'));
    await page.locator('#source-policy select').selectOption('rice');
    assert((await china.innerText()).includes('稻谷转精米定义未验证'));
    assert((await china.innerText()).includes('PSD'));
    assert(!(await page.locator('main').innerText()).includes('海外历史与预测统一用'));
    await visit('/events/?event=2023-05&crop=corn');
    assert.equal(await page.getByLabel('年度数据源', { exact: true }).inputValue(), 'actual_production');
    assert((await page.locator('.balance-note').innerText()).includes('真实产量数据库'));
    assert((await page.locator('.balance-note').innerText()).includes('FAOSTAT'));
    assert.equal(await page.locator('.event-balance-panel h2').innerText(), '2023 年');
    assert(!(await page.locator('.balance-table').innerText()).includes('库存消费比'));
    await page.getByLabel('年度数据源', { exact: true }).selectOption('usda_psd');
    assert((await page.locator('.balance-table').innerText()).includes('库存消费比'));
    assert((await page.locator('.balance-note').innerText()).includes('独立供需参考'));
    assert.equal(await page.getByText('各国实际产量来源与 PSD 回退', { exact: true }).count(), 0);
    await page.setViewportSize({ width: 390, height: 844 });
    for (const path of ['/methodology/', '/events/', '/corn/']) {
      await visit(path);
      assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)), path);
    }
    assert.deepEqual(errors, []);
    console.log('Source consistency browser passed: policy, actual production, independent balances, mobile.');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
