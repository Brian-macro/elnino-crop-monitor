const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({ headless: true, channel: "chrome" });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const base = process.env.TEST_URL || "http://127.0.0.1:3000";
  const select = (label) =>
    page
      .locator("label")
      .filter({ hasText: new RegExp("^" + label) })
      .locator("select");
  await page.goto(base + "/map/?crop=rice&focus=Southeast%20Asia");
  await page.locator("canvas").first().waitFor();
  await page.getByRole('button',{name:'成员国家',exact:true}).click();
  await page.waitForFunction(() =>
    document
      .querySelector(".crop-tabs button.active")
      ?.textContent.includes("Rice"),
  );
  await page.locator("#countrySelect").selectOption("Burma");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("11.00"),
  );
  const burma = await page.locator(".country-detail").innerText();
  if (!burma.includes("-8.3%"))
    throw Error("Myanmar rice comparison missing: " + burma);
  await page.getByRole("button", { name: "Sugar · 糖", exact: true }).click();
  await page.locator("#countrySelect").selectOption("Thailand");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("9.50"),
  );
  const thai = await page.locator(".country-detail").innerText();
  if (!thai.includes("-15.6%") || !thai.includes("上年 forecast"))
    throw Error("Thai sugar baseline status lost: " + thai);
  await select("YoY 对比基准").selectOption("actual");
  if (
    !(await page.locator(".country-detail").innerText()).includes(
      "缺少同口径上年数据",
    )
  )
    throw Error("Actual must not silently fall back");
  await select("YoY 对比基准").selectOption("reported");
  await page.getByRole("button", { name: "Rice · 水稻", exact: true }).click();
  await select("Geographic Focus").selectOption("East Asia");
  await page.locator("#countrySelect").selectOption("Korea, South");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("3.49"),
  );
  if (!(await page.locator(".country-detail").innerText()).includes("-1.4%"))
    throw Error("Korea rice missing");
  await page.locator("#countrySelect").selectOption("China");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("210.05"),
  );
  if (!(await page.locator(".country-detail").innerText()).includes("-0.6%"))
    throw Error("China current CropWatch rice missing");
  await page.getByRole("button", { name: "Corn · 玉米", exact: true }).click();
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("266.18"),
  );
  if (!(await page.locator(".country-detail").innerText()).includes("+1.0%"))
    throw Error("China current corn baseline missing");
  const asof = page.locator("input[type=date]");
  await asof.fill("2026-07-31");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("268.75"),
  );
  await asof.fill(new Date().toISOString().slice(0, 10));
  await select("Region / Province").selectOption("Henan");
  if (!(await page.locator(".country-detail").innerText()).includes("Henan"))
    throw Error("2026 province missing");
  await select("Region / Province").selectOption("");
  await page.getByRole("button", { name: "Rice · 水稻", exact: true }).click();
  await select("Geographic Focus").selectOption("Southeast Asia");
  await select("Source").selectOption("cropwatch");
  await page.locator("#countrySelect").selectOption("Thailand");
  await page.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("39.18"),
  );
  if (!(await page.locator(".country-detail").innerText()).includes("+4.7%"))
    throw Error("Thai CropWatch paddy missing");
  fs.mkdirSync("test-results", { recursive: true });
  await page.screenshot({
    path: path.resolve("test-results/asia-map-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  if (
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    )
  )
    throw Error("Mobile overflow");
  await page.screenshot({
    path: path.resolve("test-results/asia-map-mobile.png"),
    fullPage: true,
  });
  await browser.close();
  console.log(
    JSON.stringify({
      burma_yoy: "-8.3%",
      thailand_sugar_yoy: "-15.6%",
      korea_rice_yoy: "-1.4%",
      china_rice: 210.05,
      china_corn: 266.18,
      china_corn_july_asof: 268.75,
      thailand_cropwatch_paddy: 39.18,
      errors,
    }),
  );
  if (errors.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
