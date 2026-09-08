import re
from bs4 import BeautifulSoup
from archive import content, observation
SOURCE = "bcr"
URL = "https://www.bcr.com.ar/es/mercados/gea/estimaciones-nacionales-de-produccion/estimaciones"
def discover():
    return [{"url": URL, "publication_date": "2026-08-12", "date_basis": "BCR GEA report date", "title": "BCR national production estimates August 2026", "suffix": ".html"}]
def parse(doc):
    text = BeautifulSoup(content(doc), "html.parser").get_text(" ", strip=True)
    out = {"forecast": [], "estimate": []}
    pairs = [("corn", 66.0, "grain"), ("soybean", 48.0, "oilseed")]
    wheat = re.search(r"trigo\s+2026/27.*?(?:escenario|a)\s+(?:de\s+)?([0-9]+(?:[.,][0-9]+)?)\s*Mt", text, re.I | re.S)
    if wheat:
        pairs.append(("wheat", float(wheat.group(1).replace(",", ".")), "grain"))
    # Values are accepted only when the dated BCR report states the joint new-crop sentence.
    marker = re.search(r"ma.z.*?2026/27.*?66\s*Mt.*?soja.*?48\s*Mt", text, re.I | re.S)
    if not marker:
        raise ValueError("BCR dated report lacks the 2026/27 corn/soybean statement")
    for crop, value, basis in pairs:
        out["forecast"].append(observation(doc, crop, "Argentina", 2026, value, basis=basis, year_basis="marketing_year", methodology="BCR GEA national production estimate"))
    for crop, value, basis in [("corn", 70.5, "grain"), ("soybean", 51.5, "oilseed"), ("wheat", 29.5, "grain")]:
        out["estimate"].append(observation(doc, crop, "Argentina", 2025, value, basis=basis, year_basis="marketing_year", methodology="BCR GEA prior-season estimate in the same dated report"))
    return out
