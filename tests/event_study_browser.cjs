const { chromium } = require("playwright");
const fs = require("node:fs");
(async () => {
  const b = await chromium.launch({ headless: true, channel: "chrome" });
  const p = await b.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  const url = process.env.TEST_URL || "http://127.0.0.1:3000";
  const visit = async (route) => {
    await p.goto(url + route);
    await p.locator("h1").waitFor();
    await p.waitForFunction(
      () => !document.body.innerText.includes("正在读取已验证的研究数据"),
    );
    await p.evaluate(() => document.fonts.ready);
  };
  fs.mkdirSync("test-results", { recursive: true });
  await visit("/");
  if (!(await p.locator(".brand").innerText()).includes("Brian的厄尔尼诺看盘"))
    throw Error("Wrong brand");
  if (await p.getByText("查看历史、价格与预测修正", { exact: true }).count())
    throw Error("Removed disclosure still visible");
  await p.locator(".author-avatar").evaluate((img) => {
    if (!img.complete || !img.naturalWidth) throw Error("Avatar failed");
  });
  await visit("/about/");
  for (const text of [
    "宏观的本质，是跨资产套利。",
    "在不同宏观阶段，寻找赔率最高的资产与行业，",
    "在对的时间，吃到对的行业 β，",
    "最终形成属于宏观策略的 α。",
  ])
    if (!(await p.locator("main").innerText()).includes(text))
      throw Error("Missing Brian copy: " + text);
  await p
    .locator('img[alt="Brian的宏观研究笔记公众号图片"]')
    .evaluate((img) => {
      if (!img.complete || !img.naturalWidth) throw Error("QR failed");
    });
  await p.screenshot({
    path: "test-results/brian-desktop.png",
    fullPage: true,
  });
  await visit("/events/?event=2023-05&crop=corn");
  await p.locator("canvas").waitFor();
  if (
    !(await p.locator(".event-coverage").innerText()).includes(
      "25 / 25个月有可用观测",
    )
  )
    throw Error("Recent corn futures missing");
  if (await p.getByLabel("年度数据源", { exact: true }).inputValue() !== "actual_production")
    throw Error("Historical review must default to official actual production");
  await p.getByLabel("年度数据源", { exact: true }).selectOption("usda_psd");
  await p.locator(".balance-note").getByText("USDA PSD", { exact: false }).waitFor();
  if (!(await p.locator(".balance-table").innerText()).includes("1,231.51"))
    throw Error("2023 global corn balance missing");
  await p.screenshot({
    path: "test-results/events-futures-desktop.png",
    fullPage: true,
  });
  await p.getByLabel("供需年度", { exact: true }).selectOption("2024");
  await p.getByLabel("年度数据源", { exact: true }).selectOption("usda_wasde");
  if (!(await p.locator(".balance-table").innerText()).includes("1,234.06"))
    throw Error("WASDE year switch failed");
  await p.getByLabel("厄尔尼诺事件", { exact: true }).selectOption("1997-05");
  if (!(await p.locator(".event-coverage").innerText()).includes("数据缺失"))
    throw Error("Missing early futures fabricated");
  await p.getByLabel("海外价格", { exact: true }).selectOption("spot");
  if (
    !(await p.locator(".event-coverage").innerText()).includes(
      "海外现货：25 / 25个月有可用观测",
    )
  )
    throw Error("Explicit historic spot reference missing");
  await p.getByLabel("年度数据源", { exact: true }).selectOption("usda_psd");
  await p.locator(".balance-note").getByText("USDA PSD", { exact: false }).waitFor();
  if ((await p.locator(".balance-table").innerText()).includes("数据缺失"))
    throw Error("Historic PSD corn unavailable");
  for (const crop of ["soybean", "sugar", "rice", "wheat"]) {
    await p.getByLabel("品种", { exact: true }).selectOption(crop);
    await p.waitForFunction(
      () => !document.body.innerText.includes("正在读取已验证的研究数据"),
    );
    await p.locator("canvas").waitFor();
  }
  await p.getByLabel("厄尔尼诺事件", { exact: true }).selectOption("2023-05");
  await p.getByLabel("海外价格", { exact: true }).selectOption("futures");
  if (
    !(await p.locator(".event-coverage").innerText()).includes("内盘：数据缺失")
  )
    throw Error("WH missing months hidden");
  await p.setViewportSize({ width: 390, height: 844 });
  for (const route of ["/", "/events/?event=2023-05&crop=corn", "/about/"]) {
    await visit(route);
    if (
      await p.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      )
    )
      throw Error("Mobile overflow " + route);
    await p.screenshot({
      path: route.startsWith("/about")
        ? "test-results/brian-mobile.png"
        : route.startsWith("/events")
          ? "test-results/events-mobile.png"
          : "test-results/brand-mobile.png",
      fullPage: true,
    });
  }
  await b.close();
  console.log(
    JSON.stringify({
      brand: true,
      avatar: true,
      original_qr: true,
      disclosure_removed: true,
      futures_and_oni: true,
      psd_wasde_balance: true,
      missing_data: true,
      mobile: true,
      errors,
    }),
  );
  if (errors.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
