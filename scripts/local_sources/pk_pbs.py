"""PBS historical important crops; XLS requires xlrd>=2.0."""
import math
import re
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = "pk_pbs"
URL = "https://www.pbs.gov.pk/agriculture-sector-of-pakistan-importance-role-key-statistics/"


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    links = [a for a in BeautifulSoup(response.content, "html.parser").select("a[href]")
             if "Area and Production of Important Crops" in a.get_text(" ", strip=True)]
    if len(links) != 1:
        raise ValueError("PBS important crops download missing or ambiguous")
    return [{"url": urljoin(URL, links[0]["href"]), "suffix": ".xls", "title": "PBS Area and Production of Important Crops",
             "date_basis": "unknown XLS revision date; first observed; URL upload year is not publication year"}]


def parse_rows(rows, doc):
    normalized = [[unicodedata.normalize("NFKC", str(v)).strip() for v in row] for row in rows]
    if not any("Production" in v and "tonnes" in v and "000" in v for row in normalized[:4] for v in row):
        raise ValueError("PBS thousand tonnes unit missing")
    headers = [i for i, row in enumerate(normalized) if row[0] == "Crops/ Year"]
    if len(headers) != 1:
        raise ValueError("PBS crop header missing")
    h = headers[0]
    columns = {}
    for label, crop in [("Wheat", "wheat"), ("Maize", "corn")]:
        c = normalized[h].index(label) + 1
        if normalized[h + 1][c] != "Production":
            raise ValueError("PBS production column changed")
        columns[c] = crop
    out, conflicts = {}, set()
    for row in normalized[h + 2:]:
        match = re.fullmatch(r"((?:19|20)\d{2})-(\d{2})", row[0])
        if not match:
            continue
        year = int(match[1])
        if int(match[2]) != (year + 1) % 100:
            raise ValueError("PBS agricultural year invalid")
        for c, crop in columns.items():
            if row[c] in ("", "-", "..", "..."):
                continue
            value = float(row[c].replace(",", "")) / 1000
            if not math.isfinite(value) or value < 0:
                raise ValueError("PBS production invalid")
            key = (crop, year)
            # Exact repeats are harmless; conflicting vintages have no priority evidence.
            if key in out:
                if not math.isclose(out[key]["value"], value, rel_tol=1e-12, abs_tol=1e-12):
                    conflicts.add(key)
                continue
            out[key] = observation(doc, crop, "Pakistan", year, value, year_basis="agricultural_year_start",
                methodology="PBS important crops, thousand tonnes; agricultural year starts in target_year; conflicting duplicate years excluded")
    for key in conflicts:
        out.pop(key)
    if not out:
        raise ValueError("PBS production years missing")
    return {"estimate": list(out.values())}


def parse(doc):
    import xlrd
    sheet = xlrd.open_workbook(file_contents=content(doc)).sheet_by_index(0)
    return parse_rows([sheet.row_values(r) for r in range(sheet.nrows)], doc)
