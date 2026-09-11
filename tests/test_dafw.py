import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def adapter():
    assert importlib.util.find_spec('local_sources.dafw') is not None, 'DAFW adapter missing'
    from local_sources import dafw
    return dafw


def document():
    doc = json.loads(next((ROOT / 'data/raw/dafw').glob('*.metadata.json')).read_text())
    return dict(doc, publication_date='2026-05-27', available_date='2026-05-27')


def test_dafw_preserves_2025_crop_year_and_estimate_round():
    rows = adapter().parse(document())
    current = {r['crop']: r for r in rows['forecast']}
    assert {k: current[k]['value'] for k in ('rice', 'wheat', 'corn')} == {'rice': 154.024, 'wheat': 120.657, 'corn': 55.093}
    assert current['rice']['commodity_basis'] == 'milled'
    assert current['corn']['commodity_basis'] == 'grain'
    assert all(r['target_year'] == 2025 for r in current.values())
    assert all('Third Advance Estimates' in r['methodology'] for r in current.values())
    assert all(r['publication_date'] == '2026-05-27' for r in current.values())
    previous = {r['crop']: r['value'] for r in rows['estimate']}
    assert previous == {'rice': 150.184, 'wheat': 117.945, 'corn': 43.409}
    assert all(r['target_year'] == 2024 for r in rows['estimate'])
    assert 'sugar' not in current
    assert current['soybean']['value'] == 12.596
    assert 'soybean' not in previous


def test_dafw_rejects_missing_season_and_wrong_unit(monkeypatch):
    module = adapter()
    payload = (ROOT / document()['raw_path']).read_bytes()
    monkeypatch.setattr(module, 'content', lambda doc: payload.replace(b'million tonnes', b'thousand tonnes'))
    with pytest.raises(ValueError):
        module.parse(document())


def test_dafw_discovery_preserves_release_date(monkeypatch):
    module = adapter()
    payload = (ROOT / document()['raw_path']).read_bytes()
    class Response:
        content = payload
        def raise_for_status(self):
            pass
    monkeypatch.setattr(module.requests, 'get', lambda *a, **k: Response())
    result = module.discover()
    assert result[0]['publication_date'] == '2026-05-27'
