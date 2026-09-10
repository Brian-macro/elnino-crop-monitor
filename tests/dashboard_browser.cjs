const { chromium } = require("playwright");
const fs = require("node:fs");
(async () => {
  const b = await chromium.launch({
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
  });
  const p = await b.newPage({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  const bad = [];
  p.on("response", (r) => {
    if (r.status() >= 400) bad.push(r.url());
  });
  const url = process.env.TEST_URL || "http://127.0.0.1:3000";
  async function visit(route) {
    await p.goto(url + route);
    await p.locator("h1").waitFor();
    await p.waitForFunction(
      () => !document.body.innerText.includes("正在读取已验证的研究数据"),
    );
    await p.evaluate(() => document.fonts.ready);
  }
  fs.mkdirSync("test-results", { recursive: true });
  await visit("/");
  await p.locator("canvas").first().waitFor();
  if ((await p.locator("nav a").count()) !== 4)
    throw Error("Navigation should have four main links");
  if ((await p.locator(".rank-item").count()) !== 6)
    throw Error("Exactly top five plus Other expected");
  await p.getByText("预测同比范围", { exact: true }).waitFor();
  await p.getByText("产量缺口", { exact: true }).waitFor();
  if (await p.locator(".advanced-research").count())
    throw Error("Detailed research must start collapsed");
  if ((await p.locator(".world-panel").boundingBox()).y > 350)
    throw Error("Map must be above the fold");
  await p.screenshot({
    path: "test-results/dashboard-desktop.png",
    fullPage: true,
  });
  for (const crop of ["玉米", "大豆", "水稻", "糖", "小麦"]) {
    await p.getByRole("button", { name: crop, exact: true }).click();
    await p.waitForFunction(
      () => document.querySelectorAll(".rank-item").length === 6,
    );
  }
  await p.locator(".rank-item").filter({ hasText: "中国" }).click();
  await p.locator(".china-note").waitFor();
  await p.getByRole("button", { name: "关闭产区详情" }).click();
  await p.getByLabel("年度", { exact: true }).selectOption("2027");
  await p.getByText("该年度尚无可用预测", { exact: true }).waitFor();
  await p.getByLabel("年度", { exact: true }).selectOption("2026");
  await p.locator(".rank-item.others").click();
  await p.locator(".member-details").waitFor();
  await p.getByRole("button", { name: "关闭产区详情" }).click();
  if (await p.getByRole("button", { name: "查看历史、价格与预测修正" }).count())
    throw Error("Removed research disclosure must stay absent");
  for (const route of ["/elnino/", "/events/", "/methodology/", "/about/"])
    await visit(route);
  const widths = [390, 768, 1024];
  for (const width of widths) {
    await p.setViewportSize({ width, height: 900 });
    await visit("/");
    await p.locator("canvas").first().waitFor();
    if (
      await p.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      )
    )
      throw Error("Overflow " + width);
    await p.screenshot({
      path: `test-results/dashboard-${width}.png`,
      fullPage: true,
    });
  }
  await p.setViewportSize({ width: 390, height: 844 });
  for (const route of ["/elnino/", "/events/", "/methodology/"]) {
    await visit(route);
    if (
      await p.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      )
    )
      throw Error("Overflow " + route);
  }
  await b.close();
  console.log(
    JSON.stringify({
      top5_plus_other: true,
      map_above_fold: true,
      default_details_hidden: true,
      mobile_widths: widths,
      errors,
      bad,
    }),
  );
  if (errors.length || bad.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
