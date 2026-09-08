"""China Agricultural Supply and Demand Estimates, immutable monthly vintages."""
import re
from bs4 import BeautifulSoup
from archive import download,content,observation,save_parsed,failed
from db import connect,insert_rows,mark_source

REPORTS=[
 ('https://www.agri.cn/sj/gxxs/202508/t20250812_8758246.htm','2025-08-12'),
 ('https://scs.moa.gov.cn/jcyj/202608/t20260812_6486619.htm','2026-08-12'),
]
TABLES={'中国玉米供需平衡表':('corn','grain'),'中国大豆供需平衡表':('soybean','oilseed'),'中国食糖供需平衡表':('sugar','centrifugal_raw_value')}

def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True);out={'forecast':[],'estimate':[]}
 positions=sorted((text.find(h),h) for h in TABLES if text.find(h)>=0)
 for idx,(start,heading) in enumerate(positions):
  block=text[start:positions[idx+1][0] if idx+1<len(positions) else len(text)]
  years=[int(y) for y in re.findall(r'(20\d{2})/\d{2}',block[:500])]
  match=re.search(r'(?:食糖)?产量\s+([\d.\s]+?)\s+(?:甘蔗糖\s+[\d.\s]+\s+甜菜糖\s+[\d.\s]+\s+)?进口',block)
  if not match:continue
  values=[float(x)/100 for x in re.findall(r'\d+(?:\.\d+)?',match.group(1))]
  crop,basis=TABLES[heading]
  for year,value in zip(years,values):
   status='forecast' if year==max(years) else 'estimate'
   out[status].append(observation(doc,crop,'China',year,value,basis=basis,year_basis='marketing_year',methodology='Official CASDE supply-demand table'))
 if not out['forecast']:raise ValueError('CASDE production tables incomplete')
 return out

def main():
 con=connect();n=0;errors=[]
 for url,pub in REPORTS:
  try:
   doc=download(con,'casde',url,suffix='.html',publication_date=pub,available_date=pub,date_basis='Official dated report URL')
   batch=parse(doc)
   for status,rows in batch.items():insert_rows(con,rows,status);n+=len(rows)
   save_parsed(doc,batch)
  except Exception as e:errors.append(str(e))
 if n:mark_source(con,'casde',True,pub_date=max(p for _,p in REPORTS),rows=n,status='partial' if errors else 'ok',error='; '.join(errors) or None)
 else:failed(con,'casde','; '.join(errors))
 con.close();print('CASDE',n);return 1 if not n else 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
