# Overseas Local Forecast Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable, scheduled local forecast vintages for major overseas producers and activate only definition-compatible same-source YoY pairs in the composite.

**Architecture:** Every provider gets an isolated parser returning the existing observation contract. A shared adapter runner archives originals, inserts forecast/estimate rows, canonicalizes eligible pairs, and leaves PSD in place when either year or definition evidence is missing. Connectors are enabled one at a time after fixture, parser, live smoke and composite reconciliation checks pass.

**Tech Stack:** Python 3.12, requests, pandas/openpyxl, BeautifulSoup, pypdf, DuckDB, pytest, GitHub Actions.

---

### Task 1: Shared local-source adapter interface

**Files:**
- Create: `scripts/local_sources/__init__.py`
- Create: `scripts/fetch_local_sources.py`
- Create: `tests/test_local_source_contract.py`
- Modify: `scripts/config.py`

- [ ] Write a failing test requiring every adapter to expose `SOURCE`, `discover()`, and `parse(doc)`, and requiring returned rows to include `crop`, `country`, `target_year`, `year_basis`, `commodity_basis`, `metric`, `value`, `unit`, `available_date`, and `source_url`.
- [ ] Run `python -m pytest tests/test_local_source_contract.py -q`; expect failure.
- [ ] Implement `run_adapter(adapter, con)` so each discovered document is archived before parsing, insertions are append-only, and one provider failure calls `mark_source(..., False)` without stopping other providers.
- [ ] Run the contract test; expect PASS.
- [ ] Commit as `feat: add local forecast adapter contract`.

### Task 2: Canada AAFC

**Files:**
- Create: `scripts/local_sources/aafc.py`
- Create: `tests/test_aafc.py`
- Modify: `config/country_sources.json`

- [ ] Archive the verified 2026-07-20 page and write a failing parser test for all-wheat 35.260 Mt, corn 16.400 Mt and soybean 7.500 Mt for 2026/27, plus the corresponding 2025/26 pair.
- [ ] Implement HTML table parsing keyed by row label `Production (thousand tonnes)`, divide by 1000, preserve August-July for wheat and September-August for corn/soybeans.
- [ ] Enable Canada only after `pair_components` selects AAFC for both years and the three-crop average absolute difference versus the same-season PSD fixture remains 0.90%.
- [ ] Run `python -m pytest tests/test_aafc.py tests/test_composite.py -q`; expect PASS.
- [ ] Commit as `feat: add AAFC forecast vintages`.

### Task 3: Brazil CONAB

**Files:**
- Create: `scripts/local_sources/conab.py`
- Create: `tests/test_conab.py`
- Modify: `config/country_sources.json`

- [ ] Archive the official monthly XLSX and write failing tests for August 2026 corn 142.955 Mt, soybean 180.4635 Mt and wheat 5.8131 Mt.
- [ ] Parse the `BRASIL` row from `Milho Total`, `Soja`, `Trigo` and `Arroz Total`; map corn/soybean 2025/26 to PSD 2025 and Safra 2026 wheat to its explicit canonical crop year. Keep rice as paddy and ineligible for a milled composite.
- [ ] Add a regression test proving CONAB 2025/26 corn never enters PSD 2026/27 components.
- [ ] Run the CONAB and composite tests; expect PASS.
- [ ] Commit as `feat: add CONAB crop survey vintages`.

### Task 4: Australia ABARES, India DA&FW and South Africa CEC

**Files:**
- Create: `scripts/local_sources/abares.py`
- Create: `scripts/local_sources/dafw.py`
- Create: `scripts/local_sources/cec.py`
- Create: `tests/test_abares.py`
- Create: `tests/test_dafw.py`
- Create: `tests/test_cec.py`
- Modify: `config/country_sources.json`

- [ ] Write fixtures and failing assertions for ABARES 2026/27 wheat 29.9 Mt; DA&FW 2025/26 rice 154.024, wheat 120.657 and maize 55.093 Mt; CEC calendar-2026 maize 18.096865 and soybean 3.010175 Mt.
- [ ] Implement ABARES PDF/XLSX extraction with report date evidence; DA&FW HTML table extraction with estimate-round metadata; CEC PDF table extraction including commercial plus non-commercial maize.
- [ ] Map DA&FW and CEC 2025/26 values to PSD 2025 and add tests preventing their use in the PSD 2026/27 global component.
- [ ] Run the three parser suites plus composite tests; expect PASS.
- [ ] Commit as `feat: add ABARES DAFW and CEC forecasts`.

### Task 5: EU EC, Argentina BCR and Ukraine UGA

**Files:**
- Create: `scripts/local_sources/ec.py`
- Create: `scripts/local_sources/bcr.py`
- Create: `scripts/local_sources/uga.py`
- Create: `tests/test_ec.py`
- Create: `tests/test_bcr.py`
- Create: `tests/test_uga.py`
- Modify: `config/country_sources.json`

- [ ] Write fixtures and failing assertions for EC 2026/27 maize 51.9 Mt; BCR 2026/27 corn 66, soybean 48 and wheat 20 Mt; UGA 2026 wheat 23.7, corn 32.1 and soybean 4.6 Mt.
- [ ] Keep EC white sugar out of PSD centrifugal raw-value composition and require soft-wheat plus durum coverage before enabling total EU wheat.
- [ ] Parse BCR and UGA publication dates and crop-season labels from the primary pages; do not use syndicated news text as stored evidence.
- [ ] Add a high-divergence test showing BCR corn +20% is retained after definition checks and flagged in component evidence.
- [ ] Run the three parser suites and composite tests; expect PASS.
- [ ] Commit as `feat: add EC BCR and UGA forecasts`.

### Task 6: Schedule, coverage and production verification

**Files:**
- Modify: `config/research_policy.json`
- Modify: `scripts/validate.py`
- Modify: `docs/DATA_SOURCES.md`
- Modify: `docs/DATA_STITCHING.md`
- Modify: `.github/workflows/update-data.yml`

- [ ] Add each enabled adapter to the scheduled job with its publication cadence; keep Russia and Southeast Asia in PSD fallback until primary historical forecast endpoints pass the same contract.
- [ ] Add validation requiring paired-source YoY, non-overlapping global components, exact source document hashes, and a machine-readable fallback reason for every PSD component governed by a local rule.
- [ ] Run `python scripts/update_all.py --group crops --dry-run`; expect every enabled local source to appear once.
- [ ] Run `python -m pytest -q`, `python scripts/validate.py`, `npm run typecheck`, and `npm run build`; expect all to pass and zero hard failures.
- [ ] Commit as `feat: schedule verified local forecast sources`, push `main`, and verify the exact Actions run plus production JSON/page equality.

