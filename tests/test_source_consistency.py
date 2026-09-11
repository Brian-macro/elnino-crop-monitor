import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from db import connect, insert_rows
from dashboard import dashboard_bundle
from event_study import actual_production_rows, balance_rows
from policy import policy_bundle


def fixture_db():
    con = connect(':memory:')
    for source, when in [('usda_psd', '2026-07-01'), ('casde', '2026-08-01')]:
        url = 'https://example.org/' + source
        con.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',
                    [source, source, url, 'data/raw/test', source, when, when, when, 'fixture', source])
        for year in (2024, 2025):
            for country in (['China', 'United States'] if source == 'usda_psd' else ['China']):
                value = (100 if source == 'usda_psd' else 120) + (year - 2024) * 10
                insert_rows(con, [dict(document_id=source, source=source, source_url=url,
                    publication_date=when, available_date=when, download_timestamp=when,
                    crop='corn', country=country, region='', target_year=year,
                    year_basis='marketing_year', commodity_basis='grain', metric='production',
                    value=value, unit='Mt', methodology='fixture')], 'forecast')
    return con


def test_policy_matrix_exposes_registered_local_primary_and_fallback():
    rows = {(r['unit'], r['crop']): r for r in policy_bundle()['source_matrix']}
    assert rows['China', 'corn']['forecast'] == 'casde'
    assert rows['Canada', 'wheat']['forecast'] == 'aafc'
    assert rows['Global', 'corn']['forecast'] == 'local_composite'
    assert rows['Global', 'corn']['actual'] == 'faostat'
    assert rows['China', 'rice']['forecast'] == 'usda_psd'
    assert rows['China', 'rice']['configured_local_source'] == 'cropwatch'
    assert rows['China', 'rice']['fallback_reason'] == 'paddy_to_milled_crosswalk_unverified'


def test_dashboard_actual_composite_provenance_is_not_psd():
    con = fixture_db()
    snap = dashboard_bundle(con, 'corn')['years']['2025']
    assert snap['source'] == 'local_composite'
    assert snap['source_url'] is None  # Multiple source documents, no misleading single USDA link.
    assert snap['available_date'] == '2026-08-01'
    assert snap['china']['value'] == 130
    assert snap['china']['source'] == 'casde'
    assert snap['source_evidence']['China']['source_url'] == 'https://example.org/casde'
    assert snap['world']['yoy'] == pytest.approx((240 / 220 - 1) * 100)
    assert snap['world']['forecast_gap'] == pytest.approx(20)
    assert snap['world']['forecast_gap_pct'] == pytest.approx(20 / 220 * 100)
    con.close()


def test_national_current_is_adopted_without_cross_source_prior():
    con = fixture_db()
    con.execute("DELETE FROM forecast_production WHERE source='casde' AND target_year=2024")
    snap = dashboard_bundle(con, 'corn')['years']['2025']
    assert snap['china']['source'] == 'casde'
    assert snap['china']['value'] == 130
    assert snap['china']['previous'] is None
    assert snap['china']['yoy'] is None
    assert snap['world']['value'] == 240
    assert snap['world']['previous'] is None
    assert snap['world']['yoy'] is None
    assert snap['local_coverage_pct'] == 100  # USDA is the US national source.
    assert snap['source_evidence']['China']['comparison_reason'] == 'missing_local_prior'
    con.close()


def test_actual_coverage_does_not_claim_configured_source_was_adopted():
    from national_coverage import national_coverage
    con = fixture_db()
    coverage = national_coverage(con, {'corn': dashboard_bundle(con, 'corn')})
    rows = {r['country']: r for r in coverage['rows']}
    assert rows['China']['years']['2025']['source'] == 'casde'
    assert rows['Brazil']['configured_source'] == 'conab'
    assert rows['Brazil']['years']['2025']['adopted_national'] is False
    assert rows['Brazil']['latest_national'] is None
    con.close()


@pytest.mark.parametrize('crop,basis', [('corn', 'grain'), ('wheat', 'grain'), ('soybean', 'oilseed')])
def test_ukraine_harvest_year_pair_replaces_marketing_year_baseline(crop, basis):
    from dashboard import apply_local_pairs
    con = fixture_db()
    for year, value in [(2025, 31.1), (2026, 32.1)]:
        insert_rows(con, [dict(document_id='casde', source='uga', source_url='https://uga.ua/',
            publication_date='2026-08-11', available_date='2026-08-11',
            download_timestamp='2026-08-11', crop=crop, country='Ukraine', region='',
            target_year=year, year_basis='calendar_year', commodity_basis=basis,
            metric='production', value=value, unit='Mt', methodology='fixture')], 'forecast')
    current, previous = {'Ukraine': 30}, {'Ukraine': 29}
    evidence = apply_local_pairs(con, crop, 2026, current, previous, asof='2026-09-11')
    assert evidence['Ukraine']['source'] == 'uga'
    assert current['Ukraine'] == 32.1
    assert previous['Ukraine'] == 31.1
    con.close()


def test_event_actual_production_uses_only_actual_database_rows():
    con = fixture_db()
    con.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',
                ['nbs', 'NBS actual', 'https://example.org/nbs', 'data/raw/test', 'nbs',
                 '2026-08-02', '2026-08-02', '2026-08-02', 'fixture', 'nbs'])
    insert_rows(con, [dict(document_id='nbs', source='nbs', source_url='https://example.org/nbs',
        publication_date='2026-08-02', available_date='2026-08-02', download_timestamp='2026-08-02',
        crop='corn', country='China', region='', target_year=2025, year_basis='calendar_year',
        commodity_basis='grain', metric='production', value=88, unit='Mt',
        methodology='Official reported actual: fixture')], 'actual')
    rows = actual_production_rows(con, 'corn')['2025']
    assert rows['China']['production'] == 88
    assert rows['China']['source'] == 'nbs'
    assert rows['China']['status'] == 'actual'
    assert rows['China']['ending_stocks'] is None
    assert rows['Global']['production'] is None
    con.close()


def test_crop_details_keep_casde_instead_of_old_china_filter():
    from research import crop_bundle
    con = fixture_db()
    rows = crop_bundle(con, 'corn')['production']
    assert any(r['source'] == 'casde' and r['is_primary'] for r in rows)
    assert any(r['source'] == 'usda_psd' and r['country'] == 'China' for r in rows)
    con.close()
