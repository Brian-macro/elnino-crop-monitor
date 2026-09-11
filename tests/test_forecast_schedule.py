import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from policy import POLICY
from scheduler import select_jobs


def test_daily_forecasts_exclude_baseline_fetchers():
    jobs = select_jobs(POLICY['schedule'], {}, group='forecasts')
    assert {'wasde', 'cropwatch', 'casde', 'china_outlook'} <= {j['id'] for j in jobs}
    local = [j for j in jobs if j['script'] == 'fetch_local_sources.py']
    assert local and all(len(j['sources']) == 1 and j['args'] == ['--source', j['sources'][0]] for j in local)
    assert not {'psd', 'noaa', 'nbs', 'worldbank', 'futures'} & {j['id'] for j in jobs}


def test_forecasts_check_again_next_day_but_not_same_day():
    stamps = {s: '2026-09-08' for j in POLICY['schedule'] for s in j['sources']}
    assert select_jobs(POLICY['schedule'], stamps, '2026-09-08', group='forecasts', due=True) == []
    assert len(select_jobs(POLICY['schedule'], stamps, '2026-09-09', group='forecasts', due=True)) == len(select_jobs(POLICY['schedule'], {}, group='forecasts'))


def test_one_overdue_country_does_not_repeat_checked_countries():
    stamps = {s: '2026-09-08' for j in POLICY['schedule'] for s in j['sources']}
    stamps['bcr'] = '2026-09-07'
    jobs = select_jobs(POLICY['schedule'], stamps, '2026-09-08', group='forecasts', due=True)
    assert len(jobs) == 1
    assert jobs[0]['sources'] == ['bcr']


def test_build_fetches_nothing_and_manual_all_keeps_baseline():
    assert select_jobs(POLICY['schedule'], {}, group='build') == []
    assert 'psd' in {j['id'] for j in select_jobs(POLICY['schedule'], {}, group='all')}
