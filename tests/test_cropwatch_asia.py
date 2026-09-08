import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

APRIL_COUNTRIES = '575e9a4804d2073ee2da117e665ef4609606e06d501cb3e8cfb5067b1061f06d'
APRIL_CHINA = '2013fd70aafbd5f447561909a01c09a576577b42a3172ab69985ab9cdb3481ee'
JUNE_CHINA = '5044c629fc299e314203ab7ebce28caf730ec8ea337aefe40585918f3949f555'
AUGUST_CHINA = '3d2ee61d52e9c0460322140a73477c0a04d2ec253d35c201fcf8fe7c55151d35'
AUGUST_APPENDIX = '49319e6bcb4e391d62695e64589f019cb3929cb5589c4bde79d5efd37a15d329'
JUNE_IMAGE = '2ec99b42d2cb2400d3fd9cf24bd9e1b8951f9af7d0ce2041fa3bc07ea7db789f'
AUGUST_IMAGE = '50c19a95f24f8a6e0ecf2bfc7e83e0d154feb28e4cc40cbd161f7ff161331121'


def archived(sha):
    doc = json.loads((ROOT / 'data/raw/cropwatch' / (sha + '.metadata.json')).read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT / doc['raw_path']).read_bytes()).hexdigest() == sha
    return doc


def national(rows, country='China'):
    return {(r['crop'], r['commodity_basis'], r['metric']): r for r in rows
            if r['country'] == country and r['region'] == ''}


def test_april_real_countries_million_tons_and_no_inferred_previous_year():
    import fetch_cropwatch
    rows = fetch_cropwatch.tables(archived(APRIL_COUNTRIES), 2026)
    china = national(rows)
    assert set(k[0] for k in china) == {'corn', 'rice', 'wheat', 'soybean'}
    assert china['corn', 'grain', 'production']['value'] == pytest.approx(268.75)
    assert china['rice', 'paddy', 'production']['value'] == pytest.approx(209.71)
    assert all(r['target_year'] == 2026 and r['unit'] == 'Mt' for r in rows)
    assert not any(r['country'] in {'Sub-total', 'Others'} for r in rows)
    assert not any(r['crop'] == 'rice' and r['country'] in {'Indonesia', 'Thailand', 'Vietnam'} for r in rows)
    batch = fetch_cropwatch.parse_batch(archived(APRIL_COUNTRIES), 2026)
    assert not batch['estimate'], 'A published percentage is not an unpublished prior-year quantity'
    assert len(batch['quarantined']) == 3


def test_august_china_preserves_seasons_units_and_published_prior_year_soybean():
    import fetch_cropwatch
    batch = fetch_cropwatch.parse_batch(archived(AUGUST_CHINA), 2026)
    china = national(batch['forecast'])
    assert china['corn', 'grain', 'production']['value'] == pytest.approx(266.18)
    assert china['corn', 'grain', 'area']['value'] == pytest.approx(41.266)
    assert china['corn', 'grain', 'yield']['value'] == pytest.approx(6.450)
    assert china['rice', 'paddy_semi_late', 'production']['value'] == pytest.approx(132.10)
    assert china['rice', 'paddy_early', 'production']['value'] == pytest.approx(28.87)
    assert ('rice', 'paddy', 'production') not in china
    assert china['wheat', 'winter_wheat', 'production']['value'] == pytest.approx(140.96)
    assert china['soybean', 'oilseed', 'production']['value'] == pytest.approx(19.67)
    previous = national(batch['estimate'])
    assert previous['soybean', 'oilseed', 'production']['value'] == pytest.approx(19.26)
    assert all(r['target_year'] == 2025 and r['crop'] == 'soybean' for r in batch['estimate'])
    assert not any('sub' in r['region'].lower() or 'other' in r['region'].lower()
                   for r in batch['forecast'] + batch['estimate'])


def test_april_winter_wheat_explicit_thousand_ton_headers():
    import fetch_cropwatch
    batch = fetch_cropwatch.parse_batch(archived(APRIL_CHINA), 2026)
    assert national(batch['forecast'])['wheat', 'winter_wheat', 'production']['value'] == pytest.approx(133.623)
    assert national(batch['estimate'])['wheat', 'winter_wheat', 'production']['value'] == pytest.approx(131.962)
    assert all(r['crop'] == 'wheat' and r['commodity_basis'] == 'winter_wheat' for r in batch['forecast'])


def test_june_early_rice_thousand_tons_and_ambiguous_wheat_is_quarantined():
    import fetch_cropwatch
    batch = fetch_cropwatch.parse_batch(archived(JUNE_CHINA), 2026)
    assert national(batch['forecast'])['rice', 'paddy_early', 'production']['value'] == pytest.approx(27.517)
    assert not any(r['crop'] == 'wheat' for r in batch['forecast'] + batch['estimate'])
    assert any('caption' in item['reason'].lower() for item in batch['quarantined'])


@pytest.mark.parametrize('sha,expected', [
    (AUGUST_IMAGE, {'corn': (263.45, 266.18), 'rice': (211.33, 210.05),
                    'wheat': (139.32, 140.96), 'soybean': (19.26, 19.67)}),
    (JUNE_IMAGE, {'corn': (263.45, 268.75), 'rice': (211.33, 209.71),
                  'wheat': (139.32, 140.94), 'soybean': (19.15, 20.23)}),
])
def test_real_image_china_keeps_each_published_year_and_provenance(sha, expected):
    import fetch_cropwatch
    doc = archived(sha)
    batch = fetch_cropwatch.parse_batch(doc, 2026)
    for status, index, year in [('estimate', 0, 2025), ('forecast', 1, 2026)]:
        china = {r['crop']: r for r in batch[status] if r['country'] == 'China'}
        assert {crop: row['value'] for crop, row in china.items()} == {crop: pair[index] for crop, pair in expected.items()}
        assert all(r['target_year'] == year and r['unit'] == 'Mt' for r in batch[status])
        assert all(r['source_url'] == doc['source_url'] and sha in r['methodology'] for r in batch[status])
        assert all(r['publication_date'] is None and r['available_date'] == doc['available_date'] for r in batch[status])


def test_august_real_image_southeast_asia_missing_cells_are_not_zero():
    import fetch_cropwatch
    batch = fetch_cropwatch.parse_batch(archived(AUGUST_IMAGE), 2026)
    rows = {(r['country'], r['crop']): r['value'] for r in batch['forecast']}
    expected = {
        ('Cambodia', 'rice'): 9.84, ('Indonesia', 'corn'): 19.51, ('Indonesia', 'rice'): 71.74,
        ('Myanmar', 'rice'): 20.75, ('Philippines', 'corn'): 6.92, ('Philippines', 'rice'): 20.51,
        ('Thailand', 'corn'): 3.52, ('Thailand', 'rice'): 39.18,
        ('Vietnam', 'corn'): 4.17, ('Vietnam', 'rice'): 47.26, ('Laos', 'rice'): 3.92,
        ('Mongolia', 'wheat'): 0.41,
    }
    assert all(rows[key] == value for key, value in expected.items())
    assert ('Cambodia', 'corn') not in rows and ('Japan', 'rice') not in rows
    assert not any(country == 'Global' for country, _ in rows)
    assert all(value > 0 for value in rows.values())
    june = fetch_cropwatch.parse_batch(archived(JUNE_IMAGE), 2026)
    yoy = next(r for r in june['source_yoy'] if r['country'] == 'Philippines' and r['crop'] == 'rice')
    assert yoy['value'] == 0, 'Keep the explicitly published zero; do not recompute from rounded amounts'
    printed = next(r for r in batch['source_yoy'] if r['country'] == 'India' and r['crop'] == 'rice')
    assert printed['value'] == 9.6, 'Even an inconsistent printed sign must not be silently corrected'
    assert any('conflicts' in note for note in batch['coverage_notes'])


def test_image_transcription_rejects_changed_bytes_or_unknown_hash(monkeypatch):
    import fetch_cropwatch
    doc = archived(AUGUST_IMAGE)
    monkeypatch.setattr(fetch_cropwatch, 'content', lambda _: b'changed source bytes')
    with pytest.raises(ValueError, match='hash|SHA'):
        fetch_cropwatch.parse_batch(doc, 2026)
    unknown = {**doc, 'sha256': hashlib.sha256(b'changed source bytes').hexdigest()}
    with pytest.raises(ValueError, match='review|transcri|hash|SHA'):
        fetch_cropwatch.parse_batch(unknown, 2026)


def test_real_report_discovers_china_appendix_and_actual_table_image():
    import fetch_cropwatch
    doc = archived(AUGUST_APPENDIX)
    sections = fetch_cropwatch.discover_sections(doc)
    assert 'http://cloud.cropwatch.com.cn/web/report/detail?id=325&sectionId=7954' in sections
    assert doc['source_url'] in sections
    assert fetch_cropwatch.table_images(doc) == [archived(AUGUST_IMAGE)['source_url']]
