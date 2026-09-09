import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from policy import POLICY
from scheduler import select_jobs


def test_daily_forecasts_exclude_baseline_fetchers():
    jobs = select_jobs(POLICY['schedule'], {}, group='forecasts')
    assert {j['id'] for j in jobs} == {
        'wasde', 'cropwatch', 'casde', 'local_forecasts', 'china_outlook'
    }
    assert not {'psd', 'noaa', 'nbs', 'worldbank', 'futures'} & {j['id'] for j in jobs}


def test_forecasts_check_again_next_day_but_not_same_day():
    stamps = {s: '2026-09-08' for j in POLICY['schedule'] for s in j['sources']}
    assert select_jobs(POLICY['schedule'], stamps, '2026-09-08', group='forecasts', due=True) == []
    assert len(select_jobs(POLICY['schedule'], stamps, '2026-09-09', group='forecasts', due=True)) == 5


def test_build_fetches_nothing_and_manual_all_keeps_baseline():
    assert select_jobs(POLICY['schedule'], {}, group='build') == []
    assert 'psd' in {j['id'] for j in select_jobs(POLICY['schedule'], {}, group='all')}
