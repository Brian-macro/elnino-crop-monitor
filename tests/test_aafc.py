import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def adapter():
    assert importlib.util.find_spec('local_sources.aafc') is not None, 'AAFC adapter missing'
    from local_sources import aafc
    return aafc


def document():
    doc = json.loads(next((ROOT / 'data/raw/aafc').glob('*.metadata.json')).read_text())
    return dict(doc, publication_date='2026-07-20', available_date='2026-07-23')


def test_official_aafc_forecast_and_previous_year_pair():
    rows = adapter().parse(document())
    forecast = {r['crop']: r for r in rows['forecast']}
    assert {k: r['value'] for k, r in forecast.items()} == {'wheat': 35.260, 'corn': 16.400, 'soybean': 7.500}
    previous = {r['crop']: r for r in rows['estimate'] if r['target_year'] == 2025}
    assert {k: r['value'] for k, r in previous.items()} == {'wheat': 39.955, 'corn': 14.867, 'soybean': 6.918}
    for crop, row in forecast.items():
        assert row['target_year'] == 2026 and row['year_basis'] == 'marketing_year'
        assert row['commodity_basis'] == ('oilseed' if crop == 'soybean' else 'grain') and row['unit'] == 'Mt'
        assert row['publication_date'] == '2026-07-20' and row['available_date'] == '2026-07-23'
        assert ('August-July' if crop == 'wheat' else 'September-August') in row['methodology']
        assert 'Statistics Canada' in previous[crop]['methodology']


def test_aafc_rejects_missing_production_and_wrong_units(monkeypatch):
    module = adapter()
    payload = (ROOT / document()['raw_path']).read_bytes()
    monkeypatch.setattr(module, 'content', lambda doc: payload.replace(b'thousand', b'million'))
    with pytest.raises(ValueError):
        module.parse(document())


def test_aafc_discovery_reads_dates_from_page(monkeypatch):
    module = adapter()
    payload = (ROOT / document()['raw_path']).read_bytes()
    class Response:
        content = payload
        def raise_for_status(self):
            pass
    monkeypatch.setattr(module.requests, 'get', lambda *a, **k: Response())
    result = module.discover()
    assert result and result[-1]['publication_date'] == '2026-07-20'
    assert result[-1]['available_date'] == '2026-07-23'
