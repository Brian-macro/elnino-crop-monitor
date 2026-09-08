import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

def test_no_future_trend_leakage():
    import research
    years=list(range(2000,2013));values=[10+i for i in range(13)]
    a=research.lagged_trend(years,values)
    values[-1]=100000
    b=research.lagged_trend(years,values)
    assert a[-1]==b[-1]
    assert a[3] is None
    assert abs(a[-1]-22)<1e-8

def test_indices_and_constant_zscore():
    import research
    assert research.transform_prices([None,20,40],'indexed')==[None,100,200]
    assert research.transform_prices([10,10],'standardized')==[None,None]

def test_enso_requires_five_consecutive_seasons():
    import research
    def points(vals):return [dict(date=f'2000-{i+1:02d}-01',value=v) for i,v in enumerate(vals)]
    assert research.detect_events(points([.7,.8,.9,1.0]))==[]
    assert len(research.detect_events(points([.7,.8,.9,1.0,.8,0])))==1

def test_asof_query_rejects_future_vintage():
    import research
    rows=[{'available_date':'2026-05-12','value':100},{'available_date':'2026-06-11','value':120}]
    assert research.asof_rows(rows,'2026-05-31')==[rows[0]]

def test_noaa_age_uses_observation_period_end():
    from research import observation_period_end
    assert observation_period_end('noaa_oni','2026-07-01') == '2026-08-31'
    assert observation_period_end('noaa_nino34','2026-08-01') == '2026-08-31'

def test_rice_yield_can_exist_without_milled_production():
    from research import history_rows
    import pandas as pd
    rows=[]
    for year in range(2000,2007):
        rows.append(dict(source='usda_psd',country='China',region='',commodity_basis='paddy',year_basis='marketing_year',status='estimate',metric='yield',value=5+(year-2000)*.1,target_year=year,available_date='2026-09-08'))
    hist=history_rows(pd.DataFrame(rows))
    assert len(hist)==7
    assert hist[-1]['production'] is None
    assert hist[-1]['yield_value']==5.6
    assert hist[-1]['yield_anomaly_pct'] is not None

def test_global_psd_preserves_each_source_snapshot():
    from db import connect,insert_rows
    from research import crop_bundle
    c=connect(':memory:')
    for doc,when,value in [('old','2026-05-01',100),('new','2026-06-01',110)]:
        c.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',[doc,'usda_psd','https://example.org/'+doc,'data/raw/test','sha'+doc,when,when,when,'test fixture','test'])
        r=dict(document_id=doc,crop='corn',country='United States',region='',target_year=2026,year_basis='marketing_year',commodity_basis='grain',metric='production',value=value,unit='Mt',source='usda_psd',publication_date=when,available_date=when,download_timestamp=when,methodology='PSD test fixture',source_url='https://example.org/'+doc)
        insert_rows(c,[r],'forecast')
    result=crop_bundle(c,'corn')
    assert [r['value'] for r in result['production'] if r['country']=='Global']==[100,110]
    c.close()
