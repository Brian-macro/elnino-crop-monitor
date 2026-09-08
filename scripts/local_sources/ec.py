import re
from archive import content, observation
SOURCE='ec'
URL='https://agriculture.ec.europa.eu/document/download/0614f4db-9af5-463d-9d4b-7cc9a06c366a_en?filename=short-term-outlook-summer-2026_en.pdf'
def discover(): return [{'url':URL,'publication_date':'2026-07-03','date_basis':'European Commission publication','title':'EU short-term outlook summer 2026','suffix':'.pdf'}]
def parse(doc):
 from pypdf import PdfReader
 import io
 text='\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(content(doc))).pages); out={'forecast':[],'estimate':[]}
 m=re.search(r'EU maize.*?([0-9]+(?:\.[0-9]+)?) million t',text,re.I|re.S)
 if m: out['forecast'].append(observation(doc,'corn','European Union',2026,float(m.group(1)),basis='grain',year_basis='marketing_year',methodology='European Commission short-term outlook'))
 return out
