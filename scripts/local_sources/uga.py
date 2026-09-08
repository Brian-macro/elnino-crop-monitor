import re
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='uga'
URL='https://uga.ua/en/news/ukraine-could-potentially-export-52-mmt-in-my-2026-2027-if-the-harvest-reaches-84-6-mmt-of-grains-and-oilseeds/'
def discover(): return [{'url':URL,'publication_date':'2026-08-11','date_basis':'UGA article date','title':'UGA Ukraine 2026 harvest forecast','suffix':'.html'}]
def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True); out={'forecast':[],'estimate':[]}
 for crop,label,basis in [('wheat','wheat harvest at ([0-9.]+) MMT','grain'),('corn','corn harvest at ([0-9.]+) MMT','grain'),('soybean','soybean harvest could total ([0-9.]+) MMT','oilseed')]:
  m=re.search(label,text,re.I)
  if m: out['forecast'].append(observation(doc,crop,'Ukraine',2026,float(m.group(1)),basis=basis,year_basis='calendar_year',methodology='UGA official association harvest forecast'))
 for crop,value,basis in [('wheat',22.5,'grain'),('corn',31.1,'grain'),('soybean',5.0,'oilseed')]:
  out['estimate'].append(observation(doc,crop,'Ukraine',2025,value,basis=basis,year_basis='calendar_year',methodology='UGA prior-harvest comparison in the same dated release'))
 return out
