# YoY-First Local Composite Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-safe, same-source paired YoY composite with CASDE and CropWatch for China, PSD fallback, a baseline comparison API, and YoY-first dashboard presentation.

**Architecture:** A registry selects one source per country/crop and maps its crop year and commodity basis to the canonical PSD definition. The composite engine replaces both current and prior PSD country components only when a compatible local pair exists; otherwise both years remain PSD. The existing static JSON publication path exposes both composite and baseline without adding a server dependency.

**Tech Stack:** Python 3.12, DuckDB, pandas, BeautifulSoup, pytest, Next.js 14, React 18, TypeScript, ECharts, GitHub Actions.

---

### Task 1: Source registry and crosswalk contract

**Files:**
- Create: `config/country_sources.json`
- Create: `tests/test_composite_policy.py`
- Modify: `scripts/policy.py`

- [ ] **Step 1: Write the failing registry tests**

```python
def test_china_sources_are_crop_specific():
    from policy import local_source
    assert local_source("China", "corn") == "casde"
    assert local_source("China", "soybean") == "casde"
    assert local_source("China", "sugar") == "casde"
    assert local_source("China", "wheat") == "cropwatch"
    assert local_source("China", "rice") == "cropwatch"

def test_unverified_crosswalk_is_not_composite_eligible():
    from policy import composite_rule
    assert not composite_rule("China", "rice")["eligible"]
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `python -m pytest tests/test_composite_policy.py -q`
Expected: FAIL because `local_source` and `composite_rule` do not exist.

- [ ] **Step 3: Add the registry**

```json
{
  "version": "2026-09-09-local-yoy-v1",
  "rules": [
    {"country":"China","crop":"corn","source":"casde","year_basis":"marketing_year","commodity_basis":"grain","eligible":true},
    {"country":"China","crop":"soybean","source":"casde","year_basis":"marketing_year","commodity_basis":"oilseed","eligible":true},
    {"country":"China","crop":"sugar","source":"casde","year_basis":"marketing_year","commodity_basis":"centrifugal_raw_value","eligible":true},
    {"country":"China","crop":"wheat","source":"cropwatch","year_basis":"calendar_year","commodity_basis":"grain","eligible":true,"target_year_offset":0},
    {"country":"China","crop":"rice","source":"cropwatch","year_basis":"calendar_year","commodity_basis":"paddy","eligible":false,"reason":"paddy_to_milled_crosswalk_unverified"}
  ]
}
```

- [ ] **Step 4: Load and validate the registry in `scripts/policy.py`**

```python
COUNTRY_SOURCE_PATH = POLICY_PATH.with_name("country_sources.json")
COUNTRY_SOURCES = json.loads(COUNTRY_SOURCE_PATH.read_text(encoding="utf-8"))

def composite_rule(country, crop):
    return next((r for r in COUNTRY_SOURCES["rules"] if r["country"] == country and r["crop"] == crop), None)

def local_source(country, crop):
    rule = composite_rule(country, crop)
    return rule["source"] if rule else None
```

Validate uniqueness of `(country, crop)`, allowed crops, required definition fields, and explicit reason for every disabled rule.

- [ ] **Step 5: Run and commit**

Run: `python -m pytest tests/test_composite_policy.py -q`
Expected: PASS.

```bash
git add config/country_sources.json scripts/policy.py tests/test_composite_policy.py
git commit -m "feat: add crop-specific local source registry"
```

### Task 2: Composite persistence schema

**Files:**
- Modify: `scripts/db.py`
- Modify: `docs/schema.sql`
- Modify: `scripts/export_database.py`
- Modify: `scripts/build_database.py`
- Modify: `scripts/validate.py`
- Create: `tests/test_composite_schema.py`

- [ ] **Step 1: Write the failing schema test**

```python
def test_composite_tables_preserve_component_evidence():
    from db import connect
    c = connect(":memory:")
    names = {r[0] for r in c.execute("show tables").fetchall()}
    assert {"canonical_production", "composite_vintage"} <= names
    cols = {r[1] for r in c.execute("pragma table_info('composite_vintage')").fetchall()}
    assert {"baseline_value", "composite_value", "previous_value", "yoy", "components_json"} <= cols
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/test_composite_schema.py -q`
Expected: FAIL with missing tables.

- [ ] **Step 3: Add append-only tables to `DDL`**

```sql
CREATE TABLE IF NOT EXISTS canonical_production (
 record_id VARCHAR PRIMARY KEY, source_record_id VARCHAR NOT NULL,
 crop VARCHAR NOT NULL, country VARCHAR NOT NULL, target_year INTEGER NOT NULL,
 metric VARCHAR NOT NULL, value DOUBLE NOT NULL, unit VARCHAR NOT NULL,
 year_basis VARCHAR NOT NULL, commodity_basis VARCHAR NOT NULL,
 source VARCHAR NOT NULL, available_date DATE NOT NULL,
 conversion_id VARCHAR, conversion_evidence_url VARCHAR,
 UNIQUE(source_record_id, conversion_id));
CREATE TABLE IF NOT EXISTS composite_vintage (
 record_id VARCHAR PRIMARY KEY, crop VARCHAR NOT NULL, target_year INTEGER NOT NULL,
 available_date DATE NOT NULL, baseline_value DOUBLE NOT NULL,
 composite_value DOUBLE NOT NULL, previous_value DOUBLE,
 baseline_yoy DOUBLE, yoy DOUBLE, change_mt DOUBLE,
 local_coverage_pct DOUBLE NOT NULL, components_json JSON NOT NULL,
 policy_version VARCHAR NOT NULL);
```

- [ ] **Step 4: Add both tables to export, restore, orphan and finite-value validation loops**

`export_database.py` and `build_database.py` must include the two names. `validate.py` must reject duplicate composite `(crop,target_year,available_date,policy_version)` rows and YoY rows whose `previous_value` is null.

- [ ] **Step 5: Regenerate schema, run and commit**

Run: `python scripts/db.py`

Run: `python -m pytest tests/test_composite_schema.py tests/test_integrity.py -q`
Expected: PASS.

```bash
git add scripts/db.py docs/schema.sql scripts/export_database.py scripts/build_database.py scripts/validate.py tests/test_composite_schema.py
git commit -m "feat: persist canonical and composite vintages"
```

### Task 3: Same-source paired YoY engine

**Files:**
- Create: `scripts/composite.py`
- Create: `tests/test_composite.py`

- [ ] **Step 1: Write the failing paired-source tests**

```python
def test_local_pair_replaces_both_years():
    from composite import pair_components
    psd = {2025: {"China": 300.0, "Other": 700.0}, 2026: {"China": 310.0, "Other": 720.0}}
    local = {2025: {"China": 303.0}, 2026: {"China": 306.0}}
    out = pair_components(psd, local, 2026)
    assert out["current"] == 1026.0
    assert out["previous"] == 1003.0
    assert out["yoy"] == pytest.approx((1026 / 1003 - 1) * 100)
    assert out["components"]["China"]["source"] == "local"

def test_missing_local_prior_uses_psd_for_both_years():
    from composite import pair_components
    psd = {2025: {"China": 300.0}, 2026: {"China": 310.0}}
    local = {2026: {"China": 306.0}}
    out = pair_components(psd, local, 2026)
    assert out["current"] == 310.0 and out["previous"] == 300.0
    assert out["components"]["China"]["fallback_reason"] == "missing_local_pair"
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `python -m pytest tests/test_composite.py -q`
Expected: FAIL because `composite.py` does not exist.

- [ ] **Step 3: Implement the pure paired selector**

```python
def pair_components(psd, local, year):
    current, previous, components = {}, {}, {}
    for country in sorted(psd[year]):
        has_pair = country in local.get(year, {}) and country in local.get(year - 1, {})
        current[country] = local[year][country] if has_pair else psd[year][country]
        previous[country] = local[year - 1][country] if has_pair else psd[year - 1][country]
        components[country] = {
            "source": "local" if has_pair else "usda_psd",
            "current": current[country], "previous": previous[country],
            "change": current[country] - previous[country],
            "fallback_reason": None if has_pair else "missing_local_pair"
        }
    cur, prev = sum(current.values()), sum(previous.values())
    return {"current": cur, "previous": prev, "yoy": (cur / prev - 1) * 100 if prev else None, "components": components}
```

Add `build_composite(con, crop, target_year, asof)` to select one PSD document containing both years, select latest eligible canonical local pair as of `asof`, calculate coverage as replaced prior-year tonnes divided by PSD prior-year global tonnes, and hash the policy version plus component record IDs into `record_id`.

- [ ] **Step 4: Add integration tests for EU de-duplication, region exclusion, stale local rows, and a >10% valid divergence**

The >10% case must use the local pair and emit `high_divergence=true`; incompatible basis must fall back to PSD.

- [ ] **Step 5: Run and commit**

Run: `python -m pytest tests/test_composite.py tests/test_dashboard.py -q`
Expected: PASS.

```bash
git add scripts/composite.py tests/test_composite.py
git commit -m "feat: calculate paired-source production yoy"
```

### Task 4: CASDE immutable forecast vintages

**Files:**
- Create: `scripts/fetch_casde.py`
- Create: `tests/test_casde.py`
- Modify: `scripts/config.py`
- Modify: `config/research_policy.json`

- [ ] **Step 1: Archive the already verified 2025-08 and 2026-08 pages as parser fixtures**

Use `archive.download` in the updater; tests must read immutable files through metadata hashes. Expected production values are 2025/26 corn 296.16 Mt and soybean 21.09 Mt from the 2025-08 forecast, and 2026/27 corn 306.00 Mt, soybean 20.95 Mt and sugar 12.93 Mt from the 2026-08 forecast.

- [ ] **Step 2: Write failing parser tests**

```python
def test_casde_tables_keep_market_year_and_units():
    rows = parse_casde(archived_doc("casde_2026_08"))
    got = {(r["crop"], r["target_year"]): r["value"] for r in rows if r["metric"] == "production"}
    assert got[("corn", 2026)] == 306.0
    assert got[("soybean", 2026)] == 20.95
    assert got[("sugar", 2026)] == 12.93
    assert all(r["year_basis"] == "marketing_year" and r["unit"] == "Mt" for r in rows)
```

- [ ] **Step 3: Run and verify failure**

Run: `python -m pytest tests/test_casde.py -q`
Expected: FAIL because the module is missing.

- [ ] **Step 4: Implement explicit table extraction**

```python
TABLES = {"中国玉米供需平衡表": ("corn", "grain"), "中国大豆供需平衡表": ("soybean", "oilseed"), "中国食糖供需平衡表": ("sugar", "centrifugal_raw_value")}

def parse_casde(doc):
    text = BeautifulSoup(content(doc), "html.parser").get_text(" ", strip=True)
    rows = []
    for heading, (crop, basis) in TABLES.items():
        block = text[text.index(heading):]
        block = block[:min([p for p in (block.find(h, 1) for h in TABLES) if p > 0] or [len(block)])]
        years = [int(y) for y in re.findall(r"(20\d{2})/\d{2}", block)[:4]]
        values = [float(v) / 100 for v in re.search(r"产量\s+([\d.\s]+?)\s+进口", block).group(1).split()]
        for year, value in zip(years, values):
            rows.append(observation(doc, crop, "China", year, value, basis=basis, year_basis="marketing_year", methodology="Official CASDE forecast table"))
    return rows
```

Reject duplicate crop/year values and pages without explicit report number and date. Insert current/projection columns as `forecast`, prior reported columns as `estimate`, preserving the same source document.

- [ ] **Step 5: Register schedule and source freshness**

Add `casde` to `SOURCES`/`STALE_DAYS` and a 7-day scheduled job in `research_policy.json` using `fetch_casde.py`.

- [ ] **Step 6: Run and commit**

Run: `python -m pytest tests/test_casde.py tests/test_source_parsers.py -q`
Expected: PASS.

```bash
git add scripts/fetch_casde.py scripts/config.py config/research_policy.json tests/test_casde.py data/raw/casde data/vintage/casde
git commit -m "feat: ingest CASDE monthly forecast vintages"
```

### Task 5: Canonicalize CASDE and CropWatch China pairs

**Files:**
- Create: `scripts/canonical.py`
- Create: `tests/test_canonical.py`
- Modify: `scripts/update_all.py`

- [ ] **Step 1: Write failing canonicalization tests**

Test that CASDE corn/soybean/sugar become eligible canonical rows; CropWatch national full-year wheat becomes eligible with `target_year_offset=0`; winter wheat, province rows, and paddy rice remain ineligible.

- [ ] **Step 2: Implement `canonicalize(con, asof)`**

```python
def canonicalize(con, asof):
    con.execute("DELETE FROM canonical_production WHERE available_date=?", [asof])
    for rule in COUNTRY_SOURCES["rules"]:
        if not rule["eligible"]: continue
        rows = con.execute("""SELECT * FROM production_all WHERE source=? AND country=? AND crop=? AND region='' AND metric='production' AND available_date<=? ORDER BY available_date,download_timestamp""", [rule["source"], rule["country"], rule["crop"], asof]).fetchdf()
        # Require exact basis/year rule, then insert latest row per target year with source_record_id evidence.
```

Never mutate source observations. Hash `source_record_id`, registry version and conversion ID for the canonical record ID.

- [ ] **Step 3: Add `canonicalize` and `build_composite` as build steps after source fetches and before validation**

Run them inside the same DuckDB writer process through a new `scripts/build_composite.py`; add it to `update_all.py` before `validate.py`.

- [ ] **Step 4: Run and commit**

Run: `python -m pytest tests/test_canonical.py tests/test_composite.py -q`
Expected: PASS.

```bash
git add scripts/canonical.py scripts/build_composite.py scripts/update_all.py tests/test_canonical.py
git commit -m "feat: canonicalize local forecast pairs"
```

### Task 6: Static comparison API and dashboard ranking

**Files:**
- Modify: `scripts/dashboard.py`
- Modify: `scripts/build_web_data.py`
- Modify: `tests/test_dashboard.py`
- Modify: `lib/data.ts`

- [ ] **Step 1: Add failing dashboard contract tests**

Assert that `dashboard_bundle` returns `mode="local_composite"`, `baseline`, `world.yoy`, `world.baseline_yoy`, `world.yoy_spread_pp`, `local_coverage_pct`, and per-ranking-row `contribution_pp`. Assert top five plus other reconcile for current and previous values.

- [ ] **Step 2: Change dashboard input from raw PSD counts to composite components**

```python
summary.update(
    mode="local_composite",
    baseline={"source":"usda_psd","value":baseline_current,"previous":baseline_previous,"yoy":baseline_yoy},
    local_coverage_pct=composite["local_coverage_pct"],
)
summary["world"]["baseline_yoy"] = baseline_yoy
summary["world"]["yoy_spread_pp"] = summary["world"]["yoy"] - baseline_yoy
for row in summary["ranking"]:
    row["contribution_pp"] = row["change"] / summary["world"]["previous"] * 100 if summary["world"]["previous"] else None
```

Historical years without a stored composite use PSD and return `mode="psd_baseline"`.

- [ ] **Step 3: Publish `public/api/composite_<crop>.json` and include the current composite in `overview.json`**

Keep `dashboard_<crop>.json` as the page contract so static Pages routes do not change.

- [ ] **Step 4: Update TypeScript types and run contract tests**

Run: `python -m pytest tests/test_dashboard.py -q && npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dashboard.py scripts/build_web_data.py tests/test_dashboard.py lib/data.ts
git commit -m "feat: publish local and PSD yoy comparison"
```

### Task 7: YoY-first dashboard presentation

**Files:**
- Modify: `components/Dashboard.tsx`
- Modify: `app/globals.css`
- Modify: `tests/dashboard_browser.cjs`

- [ ] **Step 1: Add browser assertions**

Assert the primary metric label is `同比变化`, the secondary comparison contains `较 PSD`, coverage contains `本土数据覆盖`, and absolute volume remains visible but visually secondary.

- [ ] **Step 2: Update the metrics block**

Render `snapshot.world.yoy` as the largest number, followed by `yoy_spread_pp`, `change`, total value and coverage. Change ranking caption to `同比 · 对全球变化贡献`; keep production in the expanded row.

- [ ] **Step 3: Color the map by paired-source YoY and size/rank by production**

Null YoY stays neutral. The tooltip must show current, prior, YoY, contribution, selected source and fallback reason.

- [ ] **Step 4: Run browser and build checks**

Run: `npm run typecheck && npm run build`
Expected: both exit 0.

Run: `node tests/dashboard_browser.cjs`
Expected: desktop and mobile assertions pass with no console errors.

- [ ] **Step 5: Commit**

```bash
git add components/Dashboard.tsx app/globals.css tests/dashboard_browser.cjs
git commit -m "feat: make production yoy the primary dashboard signal"
```

### Task 8: Full pipeline verification and deployment documentation

**Files:**
- Modify: `docs/DATA_STITCHING.md`
- Modify: `docs/DATA_SOURCES.md`
- Modify: `docs/DEPLOYMENT.md`

- [ ] **Step 1: Build a fresh database from Parquet and run the offline pipeline**

Run: `python scripts/build_database.py --db data/processed/verification.duckdb`
Expected: restore succeeds with zero hard failures.

Run with `MONITOR_DB=data/processed/verification.duckdb`: `python scripts/update_all.py --group build --offline`
Expected: composite, validation, JSON publication and Parquet export succeed.

- [ ] **Step 2: Run all required checks once**

Run: `python -m pytest -q`
Expected: all tests pass.

Run: `python scripts/validate.py`
Expected: `0 hard failures`.

Run: `npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Document paired-source YoY and fallback behavior**

State explicitly that local current and PSD prior are never mixed, Southern Hemisphere crop seasons are mapped per crop, CropWatch paddy rice remains out of the milled composite, and absolute tonnes remain available for reconciliation.

- [ ] **Step 4: Remove the verification database and commit**

```bash
git add docs/DATA_STITCHING.md docs/DATA_SOURCES.md docs/DEPLOYMENT.md data/processed/parquet data/web public/api data/raw/casde data/vintage/casde
git commit -m "docs: explain paired-source yoy composite"
```

- [ ] **Step 5: Push `main` and verify the exact GitHub Actions run**

Run: `git push origin main`
Expected: remote `main` resolves to the local commit. Confirm the update workflow reaches a successful deploy and the production page shows the same YoY values as `public/api/dashboard_<crop>.json`.

