import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def archived(source, sha):
    return json.loads((ROOT / 'data' / 'raw' / source / (sha + '.metadata.json')).read_text(encoding='utf-8'))


def test_nbs_real_report_recognizes_rice_without_inventing_soybean():
    import fetch_nbs
    assert hasattr(fetch_nbs, 'parse_actuals'), 'Annual bulletin needs a separately validated parser'
    doc = archived('nbs', '7b3057b4bb78390a1e9c9197d968af113b6cfc240ada8dc24b01585e76d0d6fd')
    rows = fetch_nbs.parse_actuals(doc)
    production = {r['crop']: r for r in rows if r['metric'] == 'production'}
    assert set(production) == {'rice', 'corn', 'wheat'}
    assert production['rice']['value'] == pytest.approx(209.041)
    assert production['corn']['value'] == pytest.approx(301.235)
    assert production['wheat']['value'] == pytest.approx(140.072)
    assert production['rice']['commodity_basis'] == 'paddy'
    assert len(rows) == 9
    assert all(r['target_year'] == 2025 and r['year_basis'] == 'calendar_year' for r in rows)


def test_cropwatch_real_multilevel_country_and_province_tables():
    from fetch_cropwatch import tables
    doc = archived('cropwatch', 'c9ca838fdbc66a7121f237d87d7d7171b04b655d03da516ea1b800bc2105740f')
    rows = tables(doc, 2026)
    national = {r['crop']: r for r in rows if r['country'] == 'China' and r['region'] == '' and r['commodity_basis'] != 'paddy_early'}
    assert set(national) == {'rice', 'corn', 'wheat', 'soybean'}
    assert national['corn']['value'] == pytest.approx(263.45)
    assert national['rice']['value'] == pytest.approx(211.33)
    assert national['soybean']['value'] == pytest.approx(19.15)
    assert national['wheat']['value'] == pytest.approx(137.74)
    assert all(r['target_year'] == 2025 for r in rows), 'Use the table target year, not the issue year'
    anhui = [r for r in rows if r['region'] == 'Anhui' and r['crop'] == 'corn']
    assert len(anhui) == 1 and anhui[0]['value'] == pytest.approx(4.42)
    rice = {(r['commodity_basis'], r['value']) for r in rows if r['region'] == 'Anhui' and r['crop'] == 'rice'}
    assert ('paddy', 15.49) in rice
    assert ('paddy_early', 1.08) in rice
    assert not any(r['region'] in {'Subtotal', 'China Toal'} for r in rows)


def test_cropwatch_current_global_table_keeps_million_tonnes():
    from fetch_cropwatch import tables
    doc = archived('cropwatch', '0a15551c8617579a6285f7227046d61708576e298d7560191404d70fe138f337')
    rows = tables(doc, 2026)
    assert len(rows) == 4
    assert next(r for r in rows if r['crop'] == 'corn')['value'] == pytest.approx(1221.48)


def test_nbs_price_correction_uses_archive_availability():
    import fetch_nbs
    assert hasattr(fetch_nbs, 'parse_prices'), 'Price parser must preserve archive availability'
    doc = archived('china_prices', 'd7d702c7748252299d423e791d324b026659b2b84921974456609ee7f3165b4a')
    corrected = {**doc, 'available_date': '2026-09-08'}
    rows = fetch_nbs.parse_prices(corrected)
    assert len(rows) == 4
    assert all(r['available_date'] == '2026-09-08' for r in rows)
    assert all(r['date'] == '2026-08-10' for r in rows)


def test_cropwatch_winter_wheat_does_not_merge_with_all_wheat(monkeypatch):
    import fetch_cropwatch
    doc = archived('cropwatch', 'c9ca838fdbc66a7121f237d87d7d7171b04b655d03da516ea1b800bc2105740f')
    payload = (ROOT / doc['raw_path']).read_bytes()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(payload, 'html.parser')
    country_table = soup.select('table')[0]
    for cell in country_table.select('th,td'):
        if cell.get_text(strip=True) == 'Wheat':
            cell.string = 'Winter wheat'
    monkeypatch.setattr(fetch_cropwatch, 'content', lambda _: str(soup).encode('utf-8'))
    rows = fetch_cropwatch.tables(doc, 2025)
    wheat = [r for r in rows if r['country'] == 'China' and not r['region'] and r['crop'] == 'wheat']
    assert {r['commodity_basis'] for r in wheat} == {'winter_wheat', 'grain'}
