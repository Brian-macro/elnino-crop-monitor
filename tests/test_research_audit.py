import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

def test_official_oni_table_is_the_event_definition_not_raw_two_decimal_rounding():
    from fetch_noaa import parse_oni_table
    payload=b'<table><tr><td>2023</td><td>-0.5</td><td>-0.3</td><td>-0.1</td><td>0.2</td><td>0.5</td><td>0.7</td><td>1.0</td><td>1.3</td><td>1.5</td><td>1.7</td><td>1.9</td><td>2.0</td></tr></table>'
    points=parse_oni_table(payload)
    assert points[4]['date']=='2023-05-01' and points[4]['value']==.5
    from research import detect_events
    event=detect_events(points)[0]
    assert event['start']=='2023-05-01'
    assert event['criterion_met_period_end']=='2023-10-31'
    assert event['announcement_date'] is None
    assert event['strength']=='Very strong'
    partial=parse_oni_table(b'<table><tr><td>2026</td><td>-0.4</td><td>-0.2</td></tr></table>')
    assert len(partial)==2 and partial[-1]['date']=='2026-02-01'

def test_sparse_domestic_months_and_incomplete_current_month_are_not_normal_observations():
    from event_study import monthly_futures
    rows=[dict(date=f'2022-08-{d:02}',open=10,high=12,low=9,close=11,volume=1) for d in [1,2,3]]
    values,quality=monthly_futures(rows,domestic=True,today='2022-09-09')
    assert '2022-08' not in values
    assert quality['2022-08']['reason']=='thin_sample'
    rows=[dict(date=f'2022-09-{d:02}',open=10,high=12,low=9,close=11,volume=100) for d in range(1,13)]
    values,quality=monthly_futures(rows,domestic=True,today='2022-09-20')
    assert '2022-09' not in values and quality['2022-09']['reason']=='incomplete_month'

def test_ohlc_invalid_rows_do_not_enter_monthly_futures():
    from event_study import monthly_futures
    rows=[dict(date=f'2022-08-{d:02}',open=10,high=12,low=9,close=11,volume=100) for d in range(1,12)]
    rows.append(dict(date='2022-08-15',open=10,high=12,low=9,close=50,volume=100))
    values,quality=monthly_futures(rows,domestic=True,today='2022-09-09')
    assert values['2022-08']==11
    assert quality['2022-08']['invalid_ohlc']==1
    assert quality['2022-08']['n_obs']==11

def test_lanina_boundary_is_not_neutral():
    from research import strength
    assert strength(-.5)=='La Niña range'

def test_psd_freshness_uses_source_update_month_not_latest_fetch():
    from normalize import source_update_month
    import pandas as pd
    assert source_update_month(pd.DataFrame({'Calendar_Year':[2025,2026],'Month':[12,8]}))=='2026-08-01'
    assert source_update_month(pd.DataFrame({'value':[1]})) is None

def test_latest_rejected_futures_revision_cannot_revive_older_quote():
    from db import connect
    from event_study import event_bundle
    c=connect(':memory:')
    for doc,stamp,usable in [('old','2025-01-10',True),('new','2025-02-10',False)]:
        c.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',[doc,'sina_cn_corn','https://example.org/'+doc,'data/raw/test',doc,None,stamp,stamp,'fixture','fixture'])
        c.execute('''INSERT INTO futures_prices(record_id,document_id,series_id,crop,market,symbol,date,open,high,low,close,volume,usable,source,available_date)
          VALUES (?,?, 'cn_corn','corn','china','C0','2024-01-02',10,12,9,11,?,?,'sina_cn_corn',?)''',[doc,doc,100 if usable else 0,usable,stamp])
    result=event_bundle(c,'corn',climate={'events':[],'series':{}})
    assert result['series']['cn_corn']['observations']==0
    c.close()
