import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from local_sources import aafc


def test_report_directory_selects_latest_dated_release():
    payload = b'<a href="/en/sector/crops/reports-statistics/canada-outlook-principal-field-crops-2026-07-20">July</a><a href="/en/sector/crops/reports-statistics/canada-outlook-principal-field-crops-2026-08-20">August</a>'
    report = aafc.discover_html(payload)[0]
    assert report['publication_date'] == '2026-08-20'
    assert report['url'].endswith('2026-08-20')
