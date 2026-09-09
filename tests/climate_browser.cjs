const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");

(async () => {
  const browser = await chromium.launch({ headless: true, channel: "chrome" });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const original = JSON.parse(fs.readFileSync("public/api/elnino.json", "utf8"));
    let fixture = structuredClone(original);
    await page.route("**/api/elnino.json*", (route) => route.fulfill({ json: fixture }));
    const visit = async () => {
      await page.goto((process.env.TEST_URL || "http://127.0.0.1:3000") + "/elnino/");
      await page.getByText("历史周期对比", { exact: true }).waitFor();
      await page.locator("canvas").first().waitFor();
    };
    await visit();
    let text = await page.locator("main").innerText();
    for (const phrase of ["基础库归档快照", "手动维护", "不是产量或价格的因果模型", "观测指数（非预测）", "月度海温异常"])
      assert(text.includes(phrase), phrase);
    assert(!/Current|Months from T|Very Strong|monthly/.test(text));
    await page.getByRole("button", { name: "ONI", exact: true }).click();
    assert((await page.locator("main").innerText()).includes("三个月滑动平均 · 日期为中心月"));
    assert((await page.locator(".toolbar").innerText()).includes(fixture.current.ONI.date.slice(0, 7)));

    // An archived warm run crossing New Year must not reset to January or today's year.
    const makePoint = (date, value) => ({ ...original.series.ONI.at(-1), date, value });
    fixture.series.ONI = [makePoint("2000-10-01", 0.1), makePoint("2000-11-01", 0.5), makePoint("2000-12-01", 0.7), makePoint("2001-01-01", 0.9)];
    fixture.current.ONI = { ...original.current.ONI, ...fixture.series.ONI.at(-1), warm_seasons: 3 };
    await visit();
    assert((await page.locator("main").innerText()).includes("2000-11 为 T，已连续 3 个 ONI 暖季，未满历史事件所需的5季"));
    await page.getByRole("button", { name: "ONI", exact: true }).click();
    assert((await page.locator("main").innerText()).includes("2000-11 为 T"));

    fixture.series.ONI.push(makePoint("2001-02-01", 0.1));
    fixture.current.ONI = { ...fixture.current.ONI, ...fixture.series.ONI.at(-1), warm_seasons: 0 };
    await visit();
    assert((await page.locator("main").innerText()).includes("不绘制近期暖段"));
    // A missing month interrupts continuity even if all remaining values are warm.
    fixture.series.ONI = [makePoint("2000-11-01", 0.5), makePoint("2001-01-01", 0.9)];
    fixture.current.ONI = { ...fixture.current.ONI, ...fixture.series.ONI.at(-1), warm_seasons: 1 };
    await visit();
    assert((await page.locator("main").innerText()).includes("2001-01 为 T，已连续 1 个 ONI 暖季"));
    await page.setViewportSize({ width: 390, height: 844 });
    assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)), "Mobile overflow");
    assert.deepEqual(errors, []);
    console.log("Climate browser: archive labels, index switching, cross-year alignment, cold ending, missing-month continuity and mobile width passed");
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
