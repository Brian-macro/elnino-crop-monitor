import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fastapi.testclient import TestClient
from db import connect,insert_rows
import api

def test_production_api_filters_asof_and_preserves_vintage(tmp_path,monkeypatch):
    path=tmp_path/'test.duckdb';con=connect(path)
    for i,when in enumerate(['2026-05-12','2026-06-11']):
        con.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',[str(i),'usda_wasde','https://example.org/'+str(i),'data/raw/test','sha'+str(i),when,when,when,'test fixture','test'])
        row=dict(document_id=str(i),crop='wheat',country='Global',region='',target_year=2026,year_basis='marketing_year',commodity_basis='grain',metric='production',value=100+i,unit='Mt',source='usda_wasde',publication_date=when,available_date=when,download_timestamp=when,methodology='Official forecast test fixture',source_url='https://example.org/'+str(i))
        insert_rows(con,[row],'forecast')
    con.close();monkeypatch.setattr(api,'DB_PATH',path);client=TestClient(api.app)
    old=client.get('/api/production',params=dict(crop='wheat',asof='2026-05-31',status='forecast'))
    assert old.status_code==200 and len(old.json()['rows'])==1
    assert len(client.get('/api/production?crop=wheat').json()['rows'])==2
    assert client.get('/api/production?crop=wheat&status=bogus').status_code==422
    assert client.get('/api/production?crop=unknown').status_code==404

def test_outlook_api_reports_coverage_and_preserves_baseline_status(tmp_path,monkeypatch):
    path=tmp_path/'outlook.duckdb';con=connect(path)
    con.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',['asia','usda_psd','https://example.org/asia','data/raw/test','asiahash','2026-08-12','2026-08-12','2026-08-12','test fixture','test'])
    for year,value in [(2025,12),(2026,11)]:
        row=dict(document_id='asia',crop='rice',country='Burma',region='',target_year=year,year_basis='marketing_year',commodity_basis='milled',metric='production',value=value,unit='Mt',source='usda_psd',publication_date='2026-08-12',available_date='2026-08-12',download_timestamp='2026-08-12',methodology='PSD test fixture',source_url='https://example.org/asia')
        insert_rows(con,[row],'forecast')
    con.close();monkeypatch.setattr(api,'DB_PATH',path);client=TestClient(api.app)
    result=client.get('/api/outlook/rice',params=dict(target_year=2026,subregion='Southeast Asia',view='countries')).json()
    burma=next(r for r in result['rows'] if r['country']=='Burma')
    assert burma['map_name']=='Myanmar'
    assert burma['previous']['status']=='forecast'
    assert round(burma['yoy'],2)==-8.33
    assert result['coverage']['with_yoy']==1
    alias=client.get('/api/production?crop=rice&country=Myanmar').json()
    assert len(alias['rows'])==2
    old=client.get('/api/outlook/rice',params=dict(target_year=2026,asof='2026-07-31')).json()
    assert old['coverage']['with_production']==0
