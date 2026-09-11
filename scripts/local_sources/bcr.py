"""Dated BCR national projections and explicit prior-season production."""
import re
from datetime import date
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE = 'bcr'
URL = 'https://www.bcr.com.ar/es/mercados/gea/estimaciones-nacionales-de-produccion/estimaciones'
MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

def discover():
    return [dict(url=URL,title='BCR national production estimates',suffix='.html')]

def resolve_date(payload):
    text = BeautifulSoup(payload,'html.parser').get_text(' ',strip=True)
    if 'Informe de Estimación Mensual Nacional' not in text:
        raise ValueError('BCR national report heading missing')
    report = text.split('Informe de Estimación Mensual Nacional',1)[1]
    match = re.search(r'(\d{1,2}) de (\w+) de (20\d{2})',report,re.I)
    if not match: raise ValueError('BCR report publication date missing')
    month = match[2].lower().replace('setiembre','septiembre')
    stamp = f'{match[3]}-{MONTHS.index(month)+1:02d}-{int(match[1]):02d}'
    date.fromisoformat(stamp)
    return dict(publication_date=stamp,date_basis='BCR dated national report')

def parse(doc):
    soup = BeautifulSoup(content(doc),'html.parser')
    out = {'forecast': [], 'estimate': []}
    for crop,name,basis in [('corn','maiz','grain'),('soybean','soja','oilseed'),('wheat','trigo','grain')]:
        table = soup.select_one('table.bcr-estimaciones.'+name)
        if table is None: raise ValueError('BCR production table missing: '+name)
        rows = {}
        for row in table.select('tbody tr'):
            cells = row.find_all('td')
            if len(cells)!=4: raise ValueError('BCR table layout changed')
            season = re.fullmatch(r'(20\d{2})/(20\d{2})',cells[0].get_text(strip=True))
            if not season or int(season[2])!=int(season[1])+1: raise ValueError('BCR invalid season')
            value = cells[3].get_text(' ',strip=True)
            if 'MILLONES TN' not in value: raise ValueError('BCR production unit missing')
            number = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*MILLONES TN',value)
            if int(season[1]) in rows:
                raise ValueError('BCR duplicate season')
            if not number and value.strip() != 'MILLONES TN':
                raise ValueError('BCR ambiguous production value')
            rows[int(season[1])] = float(number[1].replace(',','.')) if number else None
        year = max(rows)
        if rows.get(year-1) is None: raise ValueError('BCR prior production missing')
        current = rows[year]
        if current is None:
            text = soup.get_text(' ',strip=True)
            # Explicit central projections only; ignore area and higher scenarios.
            patterns = {
                'corn': r'horizonte productivo de\s+(\d+(?:[.,]\d+)?)\s*Mt',
                'soybean': r'la producción podría dejar\s+(\d+(?:[.,]\d+)?)\s*Mt',
                'wheat': r'proyección de trigo pasa a\s+(\d+(?:[.,]\d+)?)\s*Mt',
            }
            if not re.search(rf'{year}/(?:{year+1}|{str(year+1)[2:]})',text):
                raise ValueError('BCR report season missing')
            values = {float(m.replace(',','.')) for m in re.findall(patterns[crop],text,re.I)}
            if len(values)!=1: raise ValueError('BCR forecast phrase missing or ambiguous: '+crop)
            current = values.pop()
        for status,target,value in [('forecast',year,current),('estimate',year-1,rows[year-1])]:
            out[status].append(observation(doc,crop,'Argentina',target,value,basis=basis,
                year_basis='marketing_year',methodology='BCR GEA national report; production table and explicit central projection'))
    return out
