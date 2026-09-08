const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({ headless: true, channel: "chrome" });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1080 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const failed = [];
  page.on("response", (r) => {
    if (r.status() >= 400) failed.push(r.url() + ":" + r.status());
  });
  const out = path.resolve("test-results");
  fs.mkdirSync(out, { recursive: true });
  const url = process.env.TEST_URL || "http://127.0.0.1:3000";
  async function visit(route) {
    await page.goto(url + route);
    await page.locator("main h1").waitFor();
    await page.waitForFunction(
      () => !document.body.innerText.includes("正在读取已验证的研究数据"),
    );
  }
  async function canvas() {
    await page.locator("canvas").first().waitFor();
    const result = await page
      .locator("canvas")
      .first()
      .evaluate((c) => {
        const ctx = c.getContext("2d");
        if (!ctx) return { colors: 0 };
        const d = ctx.getImageData(0, 0, c.width, c.height).data;
        const colors = new Set();
        for (let i = 0; i < d.length; i += 64)
          if (d[i + 3]) colors.add([d[i], d[i + 1], d[i + 2]].join(","));
        return { width: c.width, height: c.height, colors: colors.size };
      });
    if (result.colors < 10)
      throw Error("Canvas blank: " + JSON.stringify(result));
    return result;
  }
  const reports = [];
  await visit("/");
  reports.push({ route: "/", canvas: await canvas() });
  await page.screenshot({
    path: path.join(out, "overview-desktop.png"),
    fullPage: true,
  });
  await page
    .locator("label")
    .filter({ hasText: /^Target Year/ })
    .locator("select")
    .selectOption("2025");
  await page.locator("#countrySelect").selectOption("China");
  await page
    .locator("label")
    .filter({ hasText: /^Region \/ Province/ })
    .locator("select")
    .selectOption("Henan");
  if (!(await page.locator(".breadcrumb").innerText()).includes("Henan"))
    throw Error("Province drilldown failed");
  await page
    .locator("label")
    .filter({ hasText: /^Target Year/ })
    .locator("select")
    .selectOption("2027");
  if (!(await page.locator(".country-detail").innerText()).includes("N/A"))
    throw Error("Missing 2027 forecast fabricated");
  for (const crop of ["wheat", "corn", "soybean", "rice", "sugar"]) {
    await visit("/" + crop + "/");
    await page.getByRole("button", { name: "Raw", exact: true }).click();
    await page.getByRole("button", { name: "Z-score", exact: true }).click();
    await page.getByRole("button", { name: "Indexed", exact: true }).click();
    reports.push({ route: crop, canvas: await canvas() });
  }
  await page.getByRole("button", { name: "Corn · 玉米", exact: true }).click();
  await page.waitForURL("**/corn/");
  await page.getByRole("heading", { name: "Corn · 玉米", exact: true }).waitFor();
  await page.screenshot({
    path: path.join(out, "sugar-desktop.png"),
    fullPage: true,
  });
  await visit("/elnino/");
  await page.getByRole("button", { name: "ONI", exact: true }).click();
  reports.push({ route: "elnino", canvas: await canvas() });
  await visit("/events/");
  await page
    .locator("label")
    .filter({ hasText: /^El Niño Event/ })
    .locator("select")
    .selectOption("1997-05");
  await page
    .locator("label")
    .filter({ hasText: /^Crop/ })
    .locator("select")
    .selectOption("corn");
  reports.push({ route: "events", canvas: await canvas() });
  await page.route("**/api/soybean.json", route => route.abort());
  await page.locator("label").filter({ hasText: /^Crop/ }).locator("select").selectOption("soybean");
  await page.getByRole("button", { name: "重新加载", exact: true }).waitFor();
  await page.unroute("**/api/soybean.json");
  for (const route of ["/methodology/", "/about/", "/map/"]) await visit(route);
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of [
    "/",
    "/corn/",
    "/elnino/",
    "/events/",
    "/methodology/",
    "/about/",
  ]) {
    await visit(route);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    );
    if (overflow) throw Error("Mobile horizontal overflow " + route);
    if (route === "/")
      await page.screenshot({
        path: path.join(out, "overview-mobile.png"),
        fullPage: true,
      });
    if (route === "/corn/") {
      await page.screenshot({
        path: path.join(out, "corn-mobile.png"),
        fullPage: true,
      });
      await page.getByRole("heading", { name: "历史产量 × 国内外价格", exact: true }).scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(out,"price-mobile-viewport.png")});
    }
  }
  await browser.close();
  const result = { reports, errors, failed };
  fs.writeFileSync(
    path.join(out, "browser-report.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result, null, 2));
  if (errors.length || failed.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
