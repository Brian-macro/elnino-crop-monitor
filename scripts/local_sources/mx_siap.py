"""SIAP closing-year national crop totals through its public XAJAX GET API."""
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = "mx_siap"
URL = "https://nube.agricultura.gob.mx/cierre_agricola/"
CROPS = {"Ma\u00edz grano": "corn", "Trigo grano": "wheat", "Soya": "soybean"}


def query_url(function, args=()):
    return URL + "?" + urlencode([("xajax", function)] + [("xajaxargs[]", str(a)) for a in args])


def fragments(payload):
    root = ET.fromstring(payload)
    if root.tag != "xjx":
        raise ValueError("SIAP expected XAJAX XML")
    return {c.get("t"): BeautifulSoup(c.text or "", "html.parser")
            for c in root if c.get("p") == "innerHTML"}


def options(function, target, args=()):
    response = requests.get(query_url(function, args), timeout=(10, 35))
    response.raise_for_status()
    return {o.get_text(strip=True): o["value"] for o in fragments(response.content)[target].select("option")}


def discover():
    years = sorted([int(v) for v in options("llenaAnios", "anioagric").values() if re.fullmatch(r"\d{4}", v)], reverse=True)
    if not years:
        raise ValueError("SIAP years missing")
    out = []
    for year in years[:2]:
        crops = options("llenaCultivo", "cultivo", (year, 0, ""))
        for label in CROPS:
            if label not in crops:
                raise ValueError("SIAP grain crop missing: " + label)
            units = options("llenaUnidMed", "unidMed", (crops[label],))
            if "Tonelada" not in units:
                raise ValueError("SIAP tonne unit missing")
            # National geography, all cycles, irrigated + rainfed, all varieties.
            args = (1, year, 5, 3, 0, "--", "--", crops[label], units["Tonelada"], 0, 2, 0, 0, 0, "")
            out.append({"url": query_url("reporte", args), "suffix": ".xml",
                        "title": f"SIAP {label} {year} national agricultural year",
                        "date_basis": "unknown annual closing database revision date; first observed"})
    return out


def parse(doc):
    args = parse_qs(urlparse(doc["source_url"]).query, keep_blank_values=True).get("xajaxargs[]", [])
    if len(args) != 15 or args[0] != "1" or args[2:5] != ["5", "3", "0"]:
        raise ValueError("SIAP query is not national all-cycle total")
    soup = fragments(content(doc)).get("Resultado")
    if soup is None:
        raise ValueError("SIAP result missing")
    title = soup.select_one(".titulosTabla")
    text = title.get_text(" ", strip=True) if title else ""
    year = re.search(r"A\u00f1o:\s*(\d{4})", text)
    labels = [label for label in CROPS if label + " (ton)" in text]
    if not year or year[1] != args[1] or len(labels) != 1 or "Ciclicos - Perennes" not in text or "Riego + Temporal" not in text:
        raise ValueError("SIAP title/year/unit mismatch")
    table = soup.select_one("#Resultados-reporte")
    if table is None:
        raise ValueError("SIAP production table missing")
    rows = table.select("tr")
    header = []
    for c in rows[0].find_all(["th", "td"], recursive=False):
        header.extend([c.get_text(" ", strip=True)] * int(c.get("colspan", 1)))
    if header.count("Producci\u00f3n") != 1:
        raise ValueError("SIAP physical production column missing")
    col = header.index("Producci\u00f3n")
    totals = []
    for row in rows:
        cells = []
        for c in row.find_all(["th", "td"], recursive=False):
            cells.extend([c.get_text(" ", strip=True)] * int(c.get("colspan", 1)))
        if cells and cells[0] == "Total":
            totals.append(cells)
    if len(totals) != 1 or len(totals[0]) != len(header):
        raise ValueError("SIAP national total missing or ambiguous")
    cell = totals[0][col]
    if not re.fullmatch(r"\d[\d,]*(?:\.\d+)?", cell):
        raise ValueError("SIAP invalid production tonnes")
    crop = CROPS[labels[0]]
    return {"estimate": [observation(doc, crop, "Mexico", year[1], float(cell.replace(",", "")) / 1e6,
        basis="oilseed" if crop == "soybean" else "grain", year_basis="agricultural_year",
        methodology="SIAP closing national total; all cycles and water regimes; agricultural year label, not certified marketing-year mapping")]}
