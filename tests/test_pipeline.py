import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

def test_validator_reports_orphan_observation():
    from db import connect, insert_rows
    from validate import validate_database
    c = connect(':memory:')
    row = dict(document_id='missing', crop='wheat', country='China', region='', target_year=2025,
        year_basis='calendar_year', commodity_basis='grain', metric='production', value=100,
        unit='Mt', source='nbs', publication_date='2025-12-12', available_date='2025-12-12',
        download_timestamp='2025-12-12T00:00:00', methodology='Official reported actual: test fixture',
        source_url='https://example.org/report')
    insert_rows(c, [row], 'actual')
    failures = validate_database(c, check_files=False, require_data=False)
    assert any('orphan' in f for f in failures)
    c.close()

def test_correlations_do_not_bridge_missing_months():
    from analytics import monthly_returns, correlation
    assert monthly_returns({'2020-01': 100, '2020-03': 120}) == {}
    assert correlation([1,2,3], [1,2,3], minimum=12) is None

def test_price_monthly_aggregation_and_event_window():
    from analytics import monthly_prices, event_prices
    rows = [dict(date='2020-01-10', value=100), dict(date='2020-01-20', value=120), dict(date='2020-02-01', value=132)]
    assert monthly_prices(rows) == {'2020-01': 110, '2020-02': 132}
    result = event_prices(rows, '2020-01-01')
    assert result['change_pct'] == 20
    assert result['max_drawdown_pct'] == 0

def test_pipeline_has_isolated_failure_results(tmp_path):
    from update_all import run_steps
    failure = tmp_path / 'failure.py'
    success = tmp_path / 'success.py'
    failure.write_text('raise SystemExit(2)')
    success.write_text('print("still runs")')
    result = run_steps([('bad', [str(failure)]), ('good', [str(success)])], tmp_path)
    assert [r['returncode'] for r in result] == [2, 0]
