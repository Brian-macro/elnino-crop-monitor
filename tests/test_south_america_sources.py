import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from local_sources import bcr, conab

def report(corn='67,5', prior='70,5'):
    tables = ''.join(f'<table class="bcr-estimaciones {name}"><tbody>'
        f'<tr><td>2026/2027</td><td>10</td><td></td><td>MILLONES TN</td></tr>'
        f'<tr><td>2025/2026</td><td>11</td><td>76</td><td>{value} MILLONES TN</td></tr>'
        '</tbody></table>' for name,value in [('maiz',prior),('soja','51,5'),('trigo','29,5')])
    return (tables+'Informe de Estimación Mensual Nacional 09 de Septiembre de 2026 '
        f'horizonte productivo de {corn} Mt. acercarse a 70,5 Mt. '
        'la producción podría dejar 47,8 Mt. La proyección de trigo pasa a 21 Mt.').encode()

def test_bcr_reads_updated_production_and_date(monkeypatch):
    monkeypatch.setattr(bcr,'content',lambda doc:report('68,2','71,0'))
    monkeypatch.setattr(bcr,'observation',lambda doc,crop,country,year,value,**kw:dict(crop=crop,year=year,value=value))
    rows=bcr.parse({})
    assert rows['forecast'][0]['value']==68.2
    assert rows['estimate'][0]['value']==71
    assert [r['value'] for r in rows['forecast']]==[68.2,47.8,21]
    assert bcr.resolve_date(report())['publication_date']=='2026-09-09'

def test_bcr_rejects_missing_central_projection(monkeypatch):
    monkeypatch.setattr(bcr,'content',lambda doc:report().replace(b'horizonte productivo',b'unknown phrase'))
    with pytest.raises(ValueError,match='forecast phrase'): bcr.parse({})

@pytest.mark.parametrize('label,year',[('Safra 24/25',2024),('Safra 25/26',2025),('Safra 2025',2025),('Safra 2026',2026)])
def test_conab_crop_specific_years(label,year):
    assert conab.season_year(label)==year

def test_conab_discovers_new_issue():
    html=''.join(f'<div class="item"><h2>Survey</h2><span class="documentPublished"><span class="value">{date} 09h00</span></span><a href="https://www.gov.br/{name}.xlsx">Table</a></div>'
        for date,name in [('13/08/2026','aug'),('10/09/2026','sep')])
    item=conab.discover_html(html)[0]
    assert item['publication_date']=='2026-09-10'
    assert item['url'].endswith('sep.xlsx/@@download/file')

def test_conab_parser_uses_each_sheets_production_header(monkeypatch):
    import pandas as pd
    sheets={}
    for name,labels in [('Milho Total',('Safra 25/26','Safra 26/27')),
                        ('Soja',('Safra 25/26','Safra 26/27')),
                        ('Trigo',('Safra 2026','Safra 2027'))]:
        sheets[name]=pd.DataFrame([[None,'PRODUÇÃO (Em mil t)',None],
                                   [None,*labels],['BRASIL',7000,8000]])
    monkeypatch.setattr(conab,'content',lambda doc:b'fixture')
    monkeypatch.setattr(conab.pd,'read_excel',lambda *a,**k:sheets)
    monkeypatch.setattr(conab,'observation',lambda doc,crop,country,year,value,**kw:dict(crop=crop,year=year,value=value))
    rows=conab.parse({})
    assert [r['year'] for r in rows['forecast']]==[2026,2026,2027]
    assert [r['value'] for r in rows['forecast']]==[8,8,8]

def test_parser_revision_replaces_old_year_and_rolls_back_invalid_rows():
    from db import connect
    from fetch_local_sources import replace_parsed_document
    from archive import observation
    con=connect(':memory:')
    doc=dict(document_id='fixture',source='conab',source_url='https://example.org',
        publication_date='2026-08-13',available_date='2026-08-13',download_timestamp='2026-08-13')
    old=observation(doc,'wheat','Brazil',2025,5.8)
    new=observation(doc,'wheat','Brazil',2026,5.8)
    replace_parsed_document(con,doc,{'forecast':[old]})
    replace_parsed_document(con,doc,{'forecast':[new]})
    assert con.execute('select target_year from production_all').fetchall()==[(2026,)]
    with pytest.raises(Exception):
        replace_parsed_document(con,doc,{'forecast':[{**new,'value':-1}]})
    assert con.execute('select target_year,value from production_all').fetchall()==[(2026,5.8)]
    con.close()
