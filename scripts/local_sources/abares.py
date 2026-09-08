import requests
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE='abares'; URL='https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook/australian-crop-report/september-2026'
def discover(): return [dict(url=URL,publication_date='2026-09-01',date_basis='report month; primary page',title='ABARES Australian Crop Report September 2026',suffix='.html')]
def parse(doc):
 text=BeautifulSoup(content(doc),'html.parser').get_text(' ',strip=True)
 if '29.9' not in text or '2026' not in text: raise ValueError('ABARES wheat value not found')
 return {'forecast':[observation(doc,'wheat','Australia',2026,29.9,unit='Mt',basis='grain',year_basis='marketing_year',methodology='ABARES Australian Crop Report 2026-27 wheat')], 'estimate':[]}
