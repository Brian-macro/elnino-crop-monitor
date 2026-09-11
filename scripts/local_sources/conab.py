import io
import re
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
from archive import observation, content
SOURCE = "conab"
URL = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos/11o-levantamento-safra-2025-26/site_previsao_de_safra-por_produto-ago-2026.xlsx/@@download/file"
def discover():
    if os.environ.get('MONITOR_OFFLINE') != '1':
        response = requests.get(URL.split('/11o-levantamento')[0], timeout=(10,35))
        response.raise_for_status()
        return discover_html(response.content)
    return [{"url": URL, "publication_date": "2026-08-13", "date_basis": "official CONAB 11th survey publication", "title": "CONAB 11th Grain Survey Safra 2025/26", "suffix": ".xlsx"}]

def discover_html(payload):
    candidates = []
    for item in BeautifulSoup(payload, 'html.parser').select('div.item'):
        link = item.select_one('a[href*=".xlsx"]')
        stamp = item.select_one('.documentPublished .value')
        title = item.select_one('h2')
        if not (link and stamp and title): continue
        published = datetime.strptime(stamp.get_text(strip=True)[:10], '%d/%m/%Y').date().isoformat()
        candidates.append(dict(url=link['href'].split('/@@')[0]+'/@@download/file',
            publication_date=published,date_basis='CONAB bulletin publication date',
            title=title.get_text(' ',strip=True),suffix='.xlsx'))
    if not candidates: raise ValueError('CONAB current survey workbook not found')
    return [max(candidates,key=lambda x:x['publication_date'])]

def season_year(label):
    match = re.fullmatch(r'Safra\s+(\d{4}|\d{2})(?:/(\d{2}|\d{4}))?', str(label).strip())
    if not match: raise ValueError('Unrecognized CONAB season: '+str(label))
    year = int(match[1]); year = year+2000 if year<100 else year
    if match[2] and int(match[2]) % 100 != (year+1) % 100:
        raise ValueError('Non-consecutive CONAB season')
    return year
def parse(doc):
    sheets = pd.read_excel(io.BytesIO(content(doc)), sheet_name=None, header=None)
    out = {"forecast": [], "estimate": []}
    for crop, sheet, basis in [("corn", "Milho Total", "grain"), ("soybean", "Soja", "oilseed"), ("wheat", "Trigo", "grain")]:
        frame = sheets[sheet]
        headers = [(i,j) for i in range(min(15,len(frame))) for j in range(len(frame.columns))
                   if str(frame.iat[i,j]).strip() == 'PRODUÇÃO (Em mil t)']
        if len(headers) != 1: raise ValueError('CONAB production unit/header missing')
        i,j = headers[0]
        prior_year,current_year = season_year(frame.iat[i+1,j]),season_year(frame.iat[i+1,j+1])
        if current_year != prior_year+1: raise ValueError('CONAB years are not consecutive')
        row = frame[frame.iloc[:,0].astype(str).str.strip().eq("BRASIL")]
        if len(row) != 1: raise ValueError("CONAB BRASIL row missing: " + sheet)
        values = row.iloc[0].tolist()
        prior, current = float(values[j]) / 1000, float(values[j+1]) / 1000
        out["estimate"].append(observation(doc,crop,"Brazil",prior_year,prior,basis=basis,year_basis="marketing_year",methodology="CONAB prior season in same survey"))
        out["forecast"].append(observation(doc,crop,"Brazil",current_year,current,basis=basis,year_basis="marketing_year",methodology="CONAB official crop survey forecast"))
    return out
