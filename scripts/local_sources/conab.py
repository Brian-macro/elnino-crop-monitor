import io
import pandas as pd
from archive import observation, content
SOURCE = "conab"
URL = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/safra-de-graos/boletim-da-safra-de-graos/11o-levantamento-safra-2025-26/site_previsao_de_safra-por_produto-ago-2026.xlsx/@@download/file"
def discover():
    return [{"url": URL, "publication_date": "2026-08-13", "date_basis": "official CONAB 11th survey publication", "title": "CONAB 11th Grain Survey Safra 2025/26", "suffix": ".xlsx"}]
def parse(doc):
    sheets = pd.read_excel(io.BytesIO(content(doc)), sheet_name=None, header=None)
    out = {"forecast": [], "estimate": []}
    for crop, sheet, basis, prior_year, current_year in [("corn", "Milho Total", "grain", 2024, 2025), ("soybean", "Soja", "oilseed", 2024, 2025), ("wheat", "Trigo", "grain", 2025, 2026)]:
        frame = sheets[sheet]
        row = frame[frame.iloc[:,0].astype(str).str.strip().eq("BRASIL")]
        if len(row) != 1: raise ValueError("CONAB BRASIL row missing: " + sheet)
        values = row.iloc[0].tolist()
        prior, current = float(values[7]) / 1000, float(values[8]) / 1000
        out["estimate"].append(observation(doc,crop,"Brazil",prior_year,prior,basis=basis,year_basis="marketing_year",methodology="CONAB prior season in same survey"))
        out["forecast"].append(observation(doc,crop,"Brazil",current_year,current,basis=basis,year_basis="marketing_year",methodology="CONAB official crop survey forecast"))
    return out
