import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from db import connect, insert_rows
from dashboard import dashboard_bundle
from event_study import balance_rows
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
    con.close()


def test_event_default_production_equals_dashboard_without_mixed_supply():
    from event_study import local_production_rows
    con = fixture_db()
    dashboard = dashboard_bundle(con, 'corn')
    rows = local_production_rows(dashboard)['2025']
    assert rows['Global']['production'] == dashboard['years']['2025']['world']['value']
    assert rows['China']['production'] == 130
    assert rows['China']['source'] == 'casde'
    assert rows['Global']['stocks_to_use'] is None
    assert rows['Global']['consumption'] is None
    assert rows['Global']['ending_stocks'] is None
    assert balance_rows(con, 'corn')['usda_psd']['2025']['Global']['production'] == 220
    con.close()


def test_missing_prior_pair_is_explicit_psd_fallback_in_event():
    from event_study import local_production_rows
    con = fixture_db()
    rows = local_production_rows(dashboard_bundle(con, 'corn'))['2024']
    assert rows['China']['source'] == 'usda_psd'
    assert rows['China']['fallback_reason'] == 'missing_local_pair'
    assert rows['China']['production'] == 100
    con.close()


def test_crop_details_keep_casde_instead_of_old_china_filter():
    from research import crop_bundle
    con = fixture_db()
    rows = crop_bundle(con, 'corn')['production']
    assert any(r['source'] == 'casde' and r['is_primary'] for r in rows)
    assert any(r['source'] == 'usda_psd' and r['country'] == 'China' for r in rows)
    con.close()
