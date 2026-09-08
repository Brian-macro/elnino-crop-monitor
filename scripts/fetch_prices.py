"""Monthly World Bank prices. Spot/export benchmarks, not futures or China domestic prices."""
import hashlib,io,re
from datetime import datetime
from urllib.parse import urljoin
import pandas as pd
from bs4 import BeautifulSoup
from db import connect,mark_source
from archive import download,content,archive_bytes,save_parsed,failed
from config import SOURCES
SERIES={'wheat':'Wheat, US HRW','corn':'Maize','soybean':'Soybeans','rice':'Rice, Thai 5%','sugar':'Sugar, world'}

def main():
    con=connect()
    try:
        landing=download(con,'worldbank',SOURCES['worldbank']['url'],suffix='.html')
        soup=BeautifulSoup(content(landing),'html.parser')
        link=next(a['href'] for a in soup.select('a[href]') if 'monthly' in a.get_text().lower() and '.xls' in a['href'])
        def resolve(payload):
            head=pd.read_excel(io.BytesIO(payload),sheet_name='Monthly Prices',header=None,nrows=5)
            stamp=next(str(v) for v in head.iloc[:5,0] if 'Updated on' in str(v))
            pub=datetime.strptime(stamp.strip().replace('Updated on ','').strip(),'%B %d, %Y').date().isoformat()
            return dict(publication_date=pub,date_basis='Workbook Updated on header')
        d=download(con,'worldbank',urljoin(landing['source_url'],link),suffix='.xlsx',date_resolver=resolve)
        raw=pd.read_excel(io.BytesIO(content(d)),sheet_name='Monthly Prices',header=None)
        pub=str(d['publication_date'])
        headers=[str(v).strip() for v in raw.iloc[4]]
        rows=[]
        for crop,label in SERIES.items():
            col=headers.index(label)
            for _,r in raw.iloc[6:].iterrows():
                if not re.fullmatch(r'\d{4}M\d{2}',str(r[0])):continue
                v=pd.to_numeric(r[col],errors='coerce')
                if pd.isna(v) or v<=0:continue
                day=str(r[0]).replace('M','-')+'-01'
                unit='USD/kg' if str(raw.iloc[5,col]).strip()=='($/kg)' else 'USD/t'
                rows.append(dict(record_id=hashlib.sha256((d['document_id']+crop+day).encode()).hexdigest(),document_id=d['document_id'],
                   crop=crop,market='overseas',symbol=label,date=day,value=float(v),currency='USD',unit=unit,
                   price_type='monthly spot/export benchmark',source='worldbank',available_date=str(d['available_date'])))
        con.register('_p',pd.DataFrame(rows));con.execute('INSERT INTO prices BY NAME SELECT * FROM _p ON CONFLICT DO NOTHING')
        save_parsed(d,rows);mark_source(con,'worldbank',True,pub,observation_date=max(r['date'] for r in rows),rows=len(rows))
        print('World Bank',len(rows),pub)
    except Exception as e:failed(con,'worldbank',e);return 2
    finally:con.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
