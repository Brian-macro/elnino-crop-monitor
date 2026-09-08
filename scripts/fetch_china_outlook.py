"""Archive China Agricultural Outlook editions; only parse explicitly published quantities.
The public 2026 PDF is a summary, not a complete annual projection matrix.
"""
import re,io,argparse
from datetime import date
from urllib.parse import urljoin
import pdfplumber
from bs4 import BeautifulSoup
from archive import download,content,observation,save_parsed,failed
from db import connect,insert_rows,mark_source
from config import ROOT

def parse_summary(text,doc,edition):
    compact=re.sub(r'\s+','',text)
    rows=[]
    if edition==2026:
        # Schema-specific extraction from the published 2026 summary. Values never hard-coded.
        patterns={
          'rice':r'稻谷：.*?产量保持总体稳定，预计(2035)年([\d.]+)(万吨)',
          'wheat':r'(2035)年小麦产量达([\d.]+)(万吨)',
          'corn':r'玉米：.*?(2035)年单产.*?玉米产量达([\d.]+)(亿吨)',
          'soybean':r'大豆：.*?预计(2035)年播种面积.*?产量([\d.]+)(万吨)',
          'sugar':r'预计(2035)年食糖产量将达到([\d.]+)(万吨)',
        }
        for crop,pat in patterns.items():
            m=re.search(pat,compact)
            if not m:raise ValueError('China Outlook summary schema changed: '+crop)
            year,value,unit=m.groups();value=float(value)*(100 if unit=='亿吨' else .01)
            rows.append(observation(doc,crop,'China',year,value,basis='paddy' if crop=='rice' else 'sugar_unspecified' if crop=='sugar' else 'oilseed' if crop=='soybean' else 'grain',year_basis='calendar_year',methodology='CAMES baseline projection; 2026 public summary; explicit target-year quantity, no interpolation'))
        m=re.search(r'其中大豆产量将达到([\d.]+)万吨',compact)
        if m:rows.append(observation(doc,'soybean','China',2026,float(m[1])*.01,basis='oilseed',year_basis='calendar_year',methodology='CAMES 2026 public summary, 2026 paragraph, explicit soybean production'))
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start-year',type=int,default=2024);args=ap.parse_args()
    con=connect();n=0;errors=[];last=None
    try:
        for year in range(args.start_year,date.today().year+1):
            try:
                index=download(con,'china_outlook',f'https://aoc.caas.cn/{year}/download/',suffix='.html',title=f'AOC {year} index')
                soup=BeautifulSoup(content(index),'html.parser')
                links={urljoin(index['source_url'],a['href']) for a in soup.select('a[href]') if '.pdf' in a['href'].lower()}
                if not links:errors.append(f'{year}: no public PDF links');continue
                for url in links:
                    def resolve(payload):
                        if year!=2026:return {}
                        with pdfplumber.open(io.BytesIO(payload)) as pdf:head=''.join(p.extract_text() or '' for p in pdf.pages[:2])
                        if '今年4月20日发布' in re.sub(r'\s+','',head):return dict(publication_date='2026-04-20',date_basis='PDF preface explicitly states release date')
                        return {}
                    d=download(con,'china_outlook',url,suffix='.pdf',title=f'China Agricultural Outlook {year}',date_resolver=resolve)
                    with pdfplumber.open(io.BytesIO(content(d))) as pdf:text='\n'.join(p.extract_text() or '' for p in pdf.pages)
                    (ROOT/d['raw_path']).with_suffix('.txt').write_text(text,encoding='utf-8')
                    if not text.strip():errors.append(f'{year}: scanned PDF archived, requires reviewed table extraction');continue
                    if year==2026 and '今年4月20日发布' in re.sub(r'\s+','',text):
                        rows=parse_summary(text,d,year);insert_rows(con,rows,'forecast');save_parsed(d,rows);n+=len(rows);last='2026-04-20'
                    else:errors.append(f'{year}: edition archived; no validated quantity parser for this layout')
            except Exception as e:errors.append(f'{year}: {e}')
        if not n:raise ValueError('; '.join(errors))
        mark_source(con,'china_outlook',True,last,rows=n,status='partial',error='Public summary only; intermediate years unavailable. '+'; '.join(errors))
        print('China Outlook',n,'forecasts;',len(errors),'coverage notes')
    except Exception as e:failed(con,'china_outlook',e);return 2
    finally:con.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
