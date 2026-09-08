const { chromium } = require("playwright");
const fs = require("node:fs");
(async () => {
  const b = await chromium.launch({ headless: true, channel: "chrome" });
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  const url = process.env.TEST_URL || "http://127.0.0.1:3000";
  const select = (label) =>
    p
      .locator("label")
      .filter({ hasText: new RegExp("^" + label) })
      .locator("select");
  await p.goto(url + "/map/?crop=rice&focus=Southeast%20Asia");
  await p.locator("canvas").first().waitFor();
  await p.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("114.95"),
  );
  let text = await p.locator(".country-detail").innerText();
  if (!text.includes("8 个固定成员") || !text.includes("-1.5%"))
    throw Error("Region sum/basket/yoy wrong: " + text);
  if ((await p.locator("#countrySelect").innerText()).includes("Singapore"))
    throw Error("Excluded country shown");
  await select("Member Country").selectOption("Malaysia");
  await p.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("1.65"),
  );
  await select("Member Country").selectOption("");
  await p.getByRole("button", { name: "Sugar · 糖", exact: true }).click();
  await p.waitForFunction(() =>
    document.querySelector(".country-detail")?.innerText.includes("15.68"),
  );
  if ((await select("Member Country").innerText()).includes("Malaysia"))
    throw Error("Malaysia sugar should be excluded");
  await p.getByRole("button", { name: "成员国家", exact: true }).click();
  await p.locator("#countrySelect").selectOption("Thailand");
  if (!(await p.locator(".country-detail").innerText()).includes("9.50"))
    throw Error("Country drilldown wrong");
  await p.getByRole("button", { name: "Wheat · 小麦", exact: true }).click();
  await p.getByRole("button", { name: "研究地区", exact: true }).click();
  if (
    (await p.locator("#countrySelect").innerText()).includes("Southeast Asia")
  )
    throw Error("No Southeast Asia wheat basket expected");
  await p.goto(url + "/rice/");
  await p.locator("canvas").first().waitFor();
  await select("Region / Country").selectOption("Southeast Asia");
  await p
    .locator("h3")
    .filter({ hasText: "Historical Production Observations" })
    .waitFor();
  if (!(await p.locator("main").innerText()).includes("estimate"))
    throw Error("Regional history unavailable");
  await p.goto(url + "/methodology/#source-policy");
  await p.locator("#source-policy table").waitFor();
  if (!(await p.locator("#source-policy").innerText()).includes("USDA PSD"))
    throw Error("Source plan missing");
  await p.setViewportSize({ width: 390, height: 844 });
  await p.goto(url + "/map/?crop=rice&focus=Southeast%20Asia");
  await p.locator("canvas").first().waitFor();
  if (
    await p.evaluate(
      () => document.documentElement.scrollWidth > innerWidth + 1,
    )
  )
    throw Error("Mobile overflow");
  fs.mkdirSync("test-results", { recursive: true });
  await p.screenshot({
    path: "test-results/region-mobile.png",
    fullPage: true,
  });
  await b.close();
  console.log(
    JSON.stringify({
      region_rice: 114.95,
      region_sugar: 15.68,
      excluded_nonproducers: true,
      drilldown: true,
      source_plan: true,
      errors,
    }),
  );
  if (errors.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
