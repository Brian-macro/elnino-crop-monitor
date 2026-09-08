from pathlib import Path
import re, pandas as pd
from archive import observation, content
SOURCE='conab'
def discover():
 return [{'url':'https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos/11o-levantamento-safra-2025-26','publication_date':'2026-08-13','date_basis':'official CONAB 11th survey publication','title':'CONAB 11th Grain Survey Safra 2025/26','suffix':'.xlsx'}]
def parse(doc):
 b=content(doc); rows=[]
 try:
  sheets=pd.read_excel(__import__('io').BytesIO(b),sheet_name=None,header=None)
 except Exception:return {'forecast':[],'estimate':[]}
 for _,df in sheets.items():
  text=' '.join(str(x) for x in df.fillna('').to_numpy().ravel())
  season='2025/26' if '2025/26' in text else '2026'
  for crop,label,basis in [('corn','Milho Total','grain'),('soybean','Soja','oilseed'),('wheat','Trigo','grain'),('rice','Arroz Total','paddy')]:
   mask=df.apply(lambda r:r.astype(str).str.contains(label,case=False).any(),axis=1)
   for i in df.index[mask]:
    vals=[]
    for j in range(i,min(i+8,len(df))):
     for x in df.iloc[j].tolist():
      try: vals.append(float(str(x).replace('.','').replace(',','.')))
      except: pass
    if vals:
     val=max(vals)
     if val>1000: val/=1000
     year=2025 if season=='2025/26' else 2026
     rows.append(observation(doc,crop,'Brazil',year,val,'production','Mt',basis,'marketing_year',methodology='CONAB official crop survey forecast'))
     break
 return {'forecast':rows,'estimate':[]}
