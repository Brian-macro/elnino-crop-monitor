import re
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='uga'
URL='https://uga.ua/en/news/ukraine-could-potentially-export-52-mmt-in-my-2026-2027-if-the-harvest-reaches-84-6-mmt-of-grains-and-oilseeds/'
def discover(): return [{'url':URL,'publication_date':'2026-08-11','date_basis':'UGA article date','title':'UGA Ukraine 2026 harvest forecast','suffix':'.html'}]
def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True); out={'forecast':[],'estimate':[]}
 season=re.search(r'(20\d{2}) wheat harvest',text,re.I)
 if not season: raise ValueError('UGA harvest year missing')
 year=int(season[1])
 for crop,label,basis in [('wheat','wheat harvest at','grain'),('corn','corn harvest at','grain'),('soybean','soybean harvest could total','oilseed')]:
  m=re.search(label+r'\s+([0-9.]+) MMT\s*\((?:up|down) from ([0-9.]+) MMT in (20\d{2})\)',text,re.I)
  if not m or int(m[3]) != year-1: raise ValueError('UGA same-release crop comparison missing: '+crop)
  out['forecast'].append(observation(doc,crop,'Ukraine',year,float(m[1]),basis=basis,year_basis='calendar_year',methodology='UGA official association harvest forecast'))
  out['estimate'].append(observation(doc,crop,'Ukraine',year-1,float(m[2]),basis=basis,year_basis='calendar_year',methodology='UGA prior-harvest comparison in the same dated release'))
 return out
