"""NOAA ONI and monthly OISST Nino3.4; immutable source vintages, ordered observations."""
import hashlib,io
import pandas as pd
from bs4 import BeautifulSoup
import re
from db import connect,mark_source
from archive import download,content,failed,save_parsed
from config import SOURCES
SEASONS=['DJF','JFM','FMA','MAM','AMJ','MJJ','JJA','JAS','ASO','SON','OND','NDJ']

def parse_oni_table(payload):
    soup=BeautifulSoup(payload,'html.parser');points=[]
    for tr in soup.select('tr'):
        cells=[c.get_text(' ',strip=True).replace('−','-') for c in tr.find_all(['td','th'],recursive=False)]
        if not 2<=len(cells)<=13 or not re.fullmatch(r'\d{4}',cells[0]):continue
        year=int(cells[0])
        for month,text in enumerate(cells[1:],1):
            try:value=float(text)
            except ValueError:continue
            if -10<value<10:points.append(dict(date=f'{year}-{month:02d}-01',season=SEASONS[month-1],value=value))
    if not points:raise ValueError('Official ONI table layout changed; no annual rows found')
    return sorted({p['date']:p for p in points}.values(),key=lambda p:p['date'])

def main():
    con=connect();errors=0
    for source,index in [('noaa_oni','ONI'),('noaa_nino34','Nino3.4')]:
        try:
            doc=download(con,source,SOURCES[source]['url'],suffix='.html' if index=='ONI' else '.txt',title='NOAA published ONI ERSSTv6 table (one decimal)' if index=='ONI' else 'NOAA OISST monthly SST anomalies')
            if index=='ONI':
                parsed=parse_oni_table(content(doc))
            else:
                df=pd.read_csv(io.BytesIO(content(doc)),sep=r'\s+')
                parsed=[dict(date=f'{int(r[0])}-{int(r[1]):02d}-01',season='monthly',value=float(r[-1])) for r in df.itertuples(index=False,name=None)]
            rows=[]
            for point in parsed:
                day,season,val=point['date'],point['season'],point['value']
                if not -10<float(val)<10:continue
                if day>__import__('datetime').date.today().isoformat():continue
                rows.append(dict(record_id=hashlib.sha256((doc['document_id']+day+index).encode()).hexdigest(),
                   document_id=doc['document_id'],index_name=index,date=day,season=season,value=float(val),
                   unit='degC',source=source,available_date=doc['available_date']))
            if not rows:raise ValueError('No valid NOAA observations')
            con.register('_cl',pd.DataFrame(rows))
            con.execute('INSERT INTO climate BY NAME SELECT * FROM _cl ON CONFLICT DO NOTHING')
            save_parsed(doc,rows)
            mark_source(con,source,True,observation_date=rows[-1]['date'],rows=len(rows))
            print(source,len(rows),'latest',rows[-1]['date'],rows[-1]['value'])
        except Exception as e:failed(con,source,e);errors+=1
    con.close();return 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
