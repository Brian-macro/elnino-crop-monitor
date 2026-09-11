import re, requests, os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='aafc'; URL='https://agriculture.canada.ca/en/sector/crops/reports-statistics/canada-outlook-principal-field-crops-2026-07-20'
def discover():
 if os.environ.get('MONITOR_OFFLINE') == '1':
  return [dict(url=URL,publication_date='2026-07-20',available_date='2026-07-23',date_basis='page date modified',title='AAFC Outlook July 20 2026',suffix='.html')]
 index='https://agriculture.canada.ca/en/sector/crops/reports-statistics'
 response=requests.get(index,timeout=(10,35));response.raise_for_status()
 return discover_html(response.content,index)

def discover_html(payload,index='https://agriculture.canada.ca/en/sector/crops/reports-statistics'):
 candidates=[]
 for link in BeautifulSoup(payload,'html.parser').select('a[href]'):
  match=re.search(r'canada-outlook-principal-field-crops-(20\d{2}-\d{2}-\d{2})$',link['href'])
  if match:
   candidates.append(dict(url=urljoin(index,link['href']),publication_date=match[1],date_basis='AAFC dated monthly report',title='AAFC Outlook '+match[1],suffix='.html'))
 if not candidates: raise ValueError('AAFC dated report links missing')
 return [max(candidates,key=lambda x:x['publication_date'])]

def resolve_date(payload):
 stamps=[t.get_text(strip=True) for t in BeautifulSoup(payload,'html.parser').select('time')]
 stamps=[s for s in stamps if re.fullmatch(r'20\d{2}-\d{2}-\d{2}',s)]
 if len(set(stamps))!=1: raise ValueError('AAFC page modification date missing or ambiguous')
 return dict(available_date=stamps[0],date_basis='AAFC dated report; current page revision available no earlier than Date modified')
def parse(doc):
 s=BeautifulSoup(content(doc),'html.parser'); out={'forecast':[],'estimate':[]}
 maps={'All Wheat':('wheat','grain','August-July'),'Corn':('corn','grain','September-August'),'Soybeans':('soybean','oilseed','September-August')}
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
   year=int(m.group(1)); status='forecast' if re.search(r'note\s+f\b',y,re.I) else 'estimate'; crop,basis,season=maps[key]
   out[status].append(observation(doc,crop,'Canada',year,float(v)/1000,unit='Mt',basis=basis,year_basis='marketing_year',methodology=f'AAFC {season}; {"AAFC forecast" if status=="forecast" else "Statistics Canada estimate"}'))
 if len(out['forecast'])<1: raise ValueError('AAFC production tables incomplete')
 return out
