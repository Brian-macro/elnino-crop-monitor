import re, requests
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='aafc'; URL='https://agriculture.canada.ca/en/sector/crops/reports-statistics/canada-outlook-principal-field-crops-2026-07-20'
def discover(): return [dict(url=URL,publication_date='2026-07-20',available_date='2026-07-23',date_basis='page date modified',title='AAFC Outlook July 20 2026',suffix='.html')]
def parse(doc):
 s=BeautifulSoup(content(doc),'html.parser'); out={'forecast':[],'estimate':[]}
 maps={'All Wheat':('wheat','grain','August-July'),'Corn':('corn','grain','September-August'),'Soybeans':('soybean','grain','September-August')}
 for t in s.find_all('table'):
  cap=t.find('caption'); name=cap.get_text(' ',strip=True).split(':')[0] if cap else ''
  key=next((k for k in maps if k.lower() in name.lower()),None)
  if not key: continue
  heads=[x.get_text(' ',strip=True) for x in t.select('thead th')][1:]
  row=next((r for r in t.select('tbody tr') if 'Production' in r.get_text()),None)
  if not row: continue
  if 'thousand' not in row.get_text(' ',strip=True).lower(): raise ValueError('AAFC production unit missing')
  vals=[x.get_text(' ',strip=True).replace(',','') for x in row.select('td')]
  for y,v in zip(heads,vals):
   m=re.search(r'(20\d\d)-(20\d\d)',y)
   if not m: continue
   y=f'{m.group(1)}-{m.group(2)}'
   year=int(y[:4]); status='forecast' if year==2026 else 'estimate'; crop,basis,season=maps[key]
   out[status].append(observation(doc,crop,'Canada',year,float(v)/1000,unit='Mt',basis=basis,year_basis='marketing_year',methodology=f'AAFC {season}; {"AAFC forecast" if status=="forecast" else "Statistics Canada estimate"}'))
 if len(out['forecast'])<1: raise ValueError('AAFC production tables incomplete')
 return out
