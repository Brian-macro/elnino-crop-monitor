import re, requests
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='dafw'; URL='https://pib.gov.in/PressReleasePage.aspx?PRID=2265965&reg=3&lang=1'
def discover(): return [dict(url=URL,publication_date='2026-05-27',available_date='2026-05-27',date_basis='PIB Posted On',title='Third Advance Estimates 2025-26',suffix='.html')]
def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True)
 if 'Third Advance Estimates' not in text or '2025' not in text or 'million tonnes' not in text: raise ValueError('DAFW evidence missing')
 patterns={
  'rice':(r'rice production at ([0-9.]+) million tonnes, compared to ([0-9.]+) million tonnes in 2024', 'milled'),
  'wheat':(r'Wheat production is estimated at ([0-9.]+) million tonnes, which is [0-9.]+ million tonnes higher than last year.s ([0-9.]+) million tonnes', 'grain'),
  'corn':(r'Maize production has reached a record ([0-9.]+) million tonnes, which is [0-9.]+ million tonnes higher than last year.s production of ([0-9.]+) million tonnes', 'grain'),
 };vals={};prev={};out={'forecast':[],'estimate':[]}
 for crop,(pattern,basis) in patterns.items():
  m=re.search(pattern,text,re.I)
  if not m: raise ValueError('DAFW crop evidence missing: '+crop)
  vals[crop]=(float(m.group(1)),basis);prev[crop]=float(m.group(2))
 for crop,(v,b) in vals.items():
  out['forecast'].append(observation(doc,crop,'India',2025,v,unit='Mt',basis=b,year_basis='marketing_year',methodology='DA&FW Third Advance Estimates 2025-26'))
  out['estimate'].append(observation(doc,crop,'India',2024,prev[crop],unit='Mt',basis=b,year_basis='marketing_year',methodology='DA&FW Third Advance Estimates prior-year comparison'))
 return out
