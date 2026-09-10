const ts = require("typescript");
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = fs.readFileSync("lib/data.ts", "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const sandbox = { exports: {}, require, process };
vm.runInNewContext(compiled, sandbox);
const { preferred, revision } = sandbox.exports;
const rice = JSON.parse(fs.readFileSync("public/api/rice.json", "utf8"));
const rows = rice.production.filter(
  (r) =>
    r.country === "China" &&
    !r.region &&
    r.target_year === 2025 &&
    r.status === "forecast",
);
const chinaRice = preferred(rows, "China");
assert.equal(chinaRice.commodity_basis, "milled");
assert.equal(chinaRice.source, "usda_psd");
assert.equal(
  preferred(
    rows.filter((r) => r.commodity_basis === "paddy_early"),
    "China",
    "cropwatch",
  ).commodity_basis,
  "paddy_early",
);
const latest = {
  country: "Global",
  region: "",
  commodity_basis: "grain",
  year_basis: "marketing_year",
  target_year: 2026,
  source: "usda_wasde",
  status: "forecast",
  value: 90,
  available_date: "2026-08-12",
  download_timestamp: "2026-09-08",
};
const prior = { ...latest, value: 100, available_date: "2026-07-10" };
assert.ok(Math.abs(revision([prior, latest], latest, 1) + 10) < 1e-8);
assert.equal(revision([prior, latest], latest, 3), null);
const riceAsia = rice.production.filter(
  (r) => r.target_year === 2026 && !r.region && r.status === "forecast",
);
assert.ok(riceAsia.some((r) => r.country === "Korea, South"));
assert.ok(riceAsia.some((r) => r.country === "Burma"));
const sugar = JSON.parse(fs.readFileSync("public/api/sugar.json", "utf8"));
const thailand = preferred(
  sugar.production.filter(
    (r) =>
      r.target_year === 2026 &&
      r.status === "forecast" &&
      r.country === "Thailand" &&
      !r.region,
  ),
  "Thailand",
);
assert.equal(thailand.comparisons.reported.previous.status, "forecast");
assert.ok(
  Math.abs(thailand.comparisons.reported.yoy + 15.615562266832478) < 1e-8,
);
assert.equal(thailand.comparisons.actual.yoy, null);
console.log("Frontend research contracts passed");
