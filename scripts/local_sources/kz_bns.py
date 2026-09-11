"""BNS national gross harvest, from national rows in the regional crop workbook."""
import io
import re
from datetime import datetime
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE='kz_bns'
URL='https://stat.gov.kz/en/industries/business-statistics/stat-forrest-village-hunt-fish/dynamic-tables/'


def discover():
    response=requests.get(URL,timeout=(10,35)); response.raise_for_status()
    soup=BeautifulSoup(response.content,'html.parser')
    matches=[]
    for link in soup.select('a[href]'):
        block=link.parent.parent.parent.get_text(' ',strip=True)
        if link.get_text(strip=True)=='xlsx' and 'Specified acreage, yield and gross harvest of major crops' in block:
            stamp=re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b',block)
            if not stamp: raise ValueError('BNS workbook date missing')
            matches.append(dict(url=urljoin(URL,link['href']),suffix='.xlsx',title='BNS gross harvest of major crops',
                publication_date=datetime.strptime(stamp[1],'%d.%m.%Y').date().isoformat(),date_basis='BNS dynamic table update date'))
    if len(matches)!=1: raise ValueError('BNS gross harvest workbook missing or ambiguous')
    return matches


def parse(doc):
    sheets=pd.read_excel(io.BytesIO(content(doc)),sheet_name=None,header=None)
    candidates=[frame for frame in sheets.values() if frame.iloc[:,0].astype(str).str.strip().eq('Republic of Kazakhstan').sum()>1
                and frame.astype(str).eq('Gross harvest of basic agricultural crops').any().any()]
    if len(candidates)!=1: raise ValueError('BNS national gross harvest series not found')
    frame=candidates[0]; rows=[]
    for crop,label in [('wheat','Weat (in weight after refinement)'),('corn','Corn')]:
        headings=frame.index[frame.iloc[:,0].astype(str).str.strip().eq(label)].tolist()
        if len(headings)!=1: raise ValueError('BNS crop heading missing or ambiguous: '+crop)
        start=headings[0]
        national=next((i for i in range(start+1,min(start+10,len(frame)))
                       if str(frame.iat[i,0]).strip()=='Republic of Kazakhstan'),None)
        if national is None: raise ValueError('BNS national total missing')
        block=frame.iloc[start:national]
        if 'thousand tons' not in ' '.join(str(v) for v in block.to_numpy().ravel()).lower():
            raise ValueError('BNS production unit missing')
        headers=[]
        for _, row in block.iterrows():
            cols=[(j,int(v)) for j,v in enumerate(row) if j>0 and pd.notna(v) and re.fullmatch(r'(?:19|20)\d{2}(?:\.0)?',str(v))]
            if len(cols)>2: headers.append(cols)
        if len(headers)!=1: raise ValueError('BNS annual columns ambiguous')
        for col,year in headers[0]:
            value=frame.iat[national,col]
            if pd.isna(value) or str(value).strip() in ('..','-'): continue
            value=float(value)
            if value<0 or not __import__('math').isfinite(value): raise ValueError('BNS invalid production')
            rows.append(observation(doc,crop,'Kazakhstan',year,value/1000,basis='grain',year_basis='calendar_year',
                methodology='BNS gross harvested national production; grain weight after cleaning; thousand tons / 1000; national row only'))
    return {'estimate':rows}
