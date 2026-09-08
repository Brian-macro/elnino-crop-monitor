import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

def test_top5_and_others_are_exhaustive_and_disjoint():
    from dashboard import summarize_counts
    current={'A':100,'B':80,'C':60,'D':40,'E':20,'F':10,'G':5,'Tiny':1}
    previous={k:v/2 for k,v in current.items()}
    result=summarize_counts(current,previous,{k:[k] for k in current})
    assert [r['name'] for r in result['ranking']]==['A','B','C','D','E','其他']
    assert result['ranking'][-1]['value']==16
    assert sum(r['value'] for r in result['ranking'])==result['world']['value']==316
    assert result['ranking'][-1]['yoy']==100
    members=[c for r in result['ranking'] for c in r['members']]
    assert len(members)==len(set(members))==8

def test_region_members_not_counted_again_in_others_and_weighted_yoy():
    from dashboard import summarize_counts
    current={'Thailand':20,'Vietnam':10,'A':50,'B':40,'C':35,'D':33,'E':2,'F':1}
    previous={'Thailand':10,'Vietnam':10,'A':50,'B':40,'C':35,'D':33,'E':1,'F':1}
    units={'Southeast Asia':['Thailand','Vietnam'],**{c:[c] for c in ['A','B','C','D','E','F']}}
    result=summarize_counts(current,previous,units)
    sea=next(r for r in result['ranking'] if r['name']=='Southeast Asia')
    assert sea['yoy']==50
    other=result['ranking'][-1]
    assert other['members']==['E','F'] and other['yoy']==50
    assert sum(r['value'] for r in result['ranking'])==sum(current.values())

def test_missing_prior_member_does_not_become_zero():
    from dashboard import summarize_counts
    result=summarize_counts({'A':5,'B':4},{'A':3},{'A':['A'],'B':['B']})
    assert result['world']['previous'] is None and result['world']['yoy'] is None
    assert next(r for r in result['ranking'] if r['name']=='B')['yoy'] is None

def test_historical_ranking_includes_large_producers_outside_current_shortlist():
    from db import connect,insert_rows
    from dashboard import dashboard_bundle
    c=connect(':memory:')
    c.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',['historical','usda_psd','https://example.org/data','data/raw/test','sha',None,'2026-08-12','2026-08-12','fixture','fixture'])
    for country,value in [('Cuba',7),('Brazil',6),('China',5),('India',4),('Mexico',3),('Argentina',2)]:
        r=dict(document_id='historical',crop='sugar',country=country,region='',target_year=1960,
            year_basis='marketing_year',commodity_basis='centrifugal_raw_value',metric='production',unit='Mt',value=value,
            source='usda_psd',publication_date=None,available_date='2026-08-12',download_timestamp='2026-08-12',source_url='https://example.org/data',methodology='fixture')
        insert_rows(c,[r],'estimate')
    result=dashboard_bundle(c,'sugar')['years']['1960']
    assert result['ranking'][0]['name']=='Cuba'
    assert result['ranking'][-1]['value']==2
    c.close()
