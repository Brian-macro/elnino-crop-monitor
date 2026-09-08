import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

def row(**changes):
    result=dict(country='Thailand',region='',target_year=2026,source='usda_psd',status='forecast',
        commodity_basis='centrifugal_raw_value',year_basis='marketing_year',value=9.5,document_id='current',
        available_date='2026-09-08',publication_date=None,download_timestamp='2026-09-08T10:00:00',
        source_url='https://example.org/psd',methodology='test fixture')
    return {**result,**changes}

def test_material_producers_are_published_and_nonproducers_excluded():
    from config import COUNTRIES
    assert {'Japan','Korea, South','Korea, North','Taiwan','Burma','Cambodia','Laos','Malaysia','Thailand','Vietnam','Indonesia','Philippines'} <= set(COUNTRIES)
    assert not {'Hong Kong','Macau','Singapore'} & set(COUNTRIES)

def test_yoy_can_use_published_prior_forecast_without_relabeling():
    from outlook import enrich_comparisons
    current=row();prior=row(target_year=2025,value=11.258)
    result=enrich_comparisons([prior,current])[-1]['comparisons']
    assert result['reported']['previous']['status']=='forecast'
    assert result['reported']['yoy']==pytest.approx((9.5/11.258-1)*100)
    assert result['actual']['previous'] is None
    assert result['estimate']['previous'] is None
    assert prior['status']=='forecast'

def test_comparison_rejects_future_and_incompatible_basis():
    from outlook import enrich_comparisons
    current=row(commodity_basis='milled',available_date='2026-08-12')
    future=row(target_year=2025,value=10,commodity_basis='milled',available_date='2026-09-08')
    paddy=row(target_year=2025,value=20,commodity_basis='paddy',available_date='2026-07-10')
    result=enrich_comparisons([future,paddy,current])[-1]['comparisons']
    assert result['reported']['previous'] is None
    assert result['reported']['reason']=='no_compatible_prior_year'

def test_zero_production_does_not_appear_as_no_record_or_zero_yoy():
    from outlook import enrich_comparisons
    result=enrich_comparisons([row(target_year=2025,value=0),row(value=0)])[-1]['comparisons']['reported']
    assert result['previous']['value']==0
    assert result['yoy'] is None
    assert result['reason']=='zero_prior_year'

def test_country_aliases_preserve_source_name_and_join_map():
    from geography import canonical_country,geography_metadata
    assert canonical_country('Myanmar')=='Burma'
    assert canonical_country('South Korea')=='Korea, South'
    assert geography_metadata('Burma')['map_name']=='Myanmar'
    assert geography_metadata('Korea, South')['subregion']=='East Asia'
    assert geography_metadata('Timor-Leste')['map_name']=='East Timor'

def test_same_day_documents_survive_web_export():
    from db import connect,insert_rows
    from research import crop_bundle
    c=connect(':memory:')
    for doc,stamp,value in [('morning','2026-08-12T08:00:00',10),('afternoon','2026-08-12T10:00:00',12)]:
        c.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',[doc,'usda_wasde','https://example.org/'+doc,'data/raw/test',doc,'2026-08-12','2026-08-12',stamp,'fixture','fixture'])
        r=row(country='Thailand',source='usda_wasde',document_id=doc,value=value,available_date='2026-08-12',download_timestamp=stamp)
        r.update(crop='sugar',metric='production',unit='Mt')
        r.pop('status')
        insert_rows(c,[r],'forecast')
    exported=crop_bundle(c,'sugar')['production']
    assert [r['value'] for r in exported if r['country']=='Thailand']==[10,12]
    c.close()
