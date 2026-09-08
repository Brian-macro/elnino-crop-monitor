import re
from archive import content, observation
SOURCE='cec'
def discover():
 return [{'url':'https://www.sagis.org.za/wp-content/uploads/2026/08/CEC_2026-08-26.pdf','publication_date':'2026-08-26','date_basis':'official CEC PDF date','title':'CEC August 2026 final production estimate','suffix':'.pdf'}]
def parse(doc):
 try:
  from pypdf import PdfReader
  text='\n'.join(p.extract_text() or '' for p in PdfReader(__import__('io').BytesIO(content(doc))).pages)
 except Exception:text=content(doc).decode('utf8','ignore')
 out=[]
 for crop,pat,basis in [('corn',r'(?:maize|corn).*?([0-9]+(?:\.[0-9]+)?)','grain'),('soybean',r'(?:soybean|soya).*?([0-9]+(?:\.[0-9]+)?)','oilseed')]:
  m=re.search(pat,text,re.I|re.S)
  if m:
   out.append(observation(doc,crop,'South Africa',2026,float(m.group(1)),'production','Mt',basis,'calendar_year',methodology='CEC official estimate including commercial and non-commercial'))
 return {'forecast':out,'estimate':[]}
