import re
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='bcr'
URL='https://www.bcr.com.ar/es/mercados/gea/estimaciones-nacionales-de-produccion/estimaciones'
def discover(): return [{'url':URL,'publication_date':'2026-08-12','date_basis':'BCR GEA report date','title':'BCR national production estimates August 2026','suffix':'.html'}]
def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True); out={'forecast':[],'estimate':[]}
 for crop,pat,basis in [('wheat',r'Trigo.*?2026/2027.*?([0-9]+(?:\.[0-9]+)?) MILLONES TN','grain'),('corn',r'Maiz.*?2026/2027.*?([0-9]+(?:\.[0-9]+)?) MILLONES TN','grain'),('soybean',r'Soja.*?2026/2027.*?([0-9]+(?:\.[0-9]+)?) MILLONES TN','oilseed')]:
  m=re.search(pat,text,re.I|re.S)
  if m: out['forecast'].append(observation(doc,crop,'Argentina',2026,float(m.group(1)),basis=basis,year_basis='marketing_year',methodology='BCR GEA national production estimate'))
 return out
