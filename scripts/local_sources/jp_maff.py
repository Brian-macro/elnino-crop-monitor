"""MAFF English statistical yearbook XLS: national wheat and soybeans.

Requires xlrd>=2.0 for the official legacy XLS files (not openpyxl).
"""
import math
import re
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = "jp_maff"
URL = "https://www.maff.go.jp/e/data/stat/nenji_index.htm"


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    links = [urljoin(URL, a["href"]) for a in BeautifulSoup(response.content, "html.parser").select("a[href]")
             if re.search(r"/\d+(?:st|nd|rd|th)/index.html$", a["href"])]
    if not links:
        raise ValueError("MAFF yearbook links missing")
    latest = max(links, key=lambda u: int(re.search(r"/(\d+)(?:st|nd|rd|th)/", u)[1]))
    response = requests.get(latest, timeout=(10, 35))
    response.raise_for_status()
    out = []
    for a in BeautifulSoup(response.content, "html.parser").select('a[href$=".xls"]'):
        title = a.get_text(" ", strip=True)
        if "Wheat and Barley (as Matured Grain)" in title or "Pulses and Buckwheat" in title:
            out.append({"url": urljoin(latest, a["href"]), "suffix": ".xls", "title": title,
                        "date_basis": "unknown yearbook file publication date; first observed"})
    if len(out) != 2:
        raise ValueError("MAFF wheat/soybean files missing or ambiguous")
    return out


def parse_rows(rows, doc):
    norm = lambda x: " ".join(unicodedata.normalize("NFKC", str(x)).split())
    cells = [[norm(v) for v in row] for row in rows]
    out = []
    for label, crop in [("Wheat", "wheat"), ("Soy beans", "soybean")]:
        anchors = [(r, c) for r, row in enumerate(cells[:15]) for c, v in enumerate(row) if v == label]
        for r, c in anchors:
            # The English crop label may be centered, not at a merged range's start.
            next_group = next((i for i in range(c + 1, len(cells[r])) if cells[r][i]), len(cells[r]))
            candidates = [(rr, cc) for rr in range(r + 1, min(r + 8, len(cells)))
                          for cc in range(c, next_group) if cells[rr][cc] == "Production"]
            if len(candidates) != 1:
                raise ValueError("MAFF production column ambiguous")
            metric_row, col = candidates[0]
            unit_rows = [rr for rr in range(metric_row + 1, min(metric_row + 9, len(cells))) if cells[rr][col] == "t"]
            if len(unit_rows) != 1:
                raise ValueError("MAFF tonnes unit missing")
            year_cols = [cc for row in cells[:15] for cc, v in enumerate(row)
                         if v.lower() == "production year and prefecture"]
            if len(year_cols) != 1:
                raise ValueError("MAFF English year column missing")
            seen = set()
            for rr in range(unit_rows[0] + 1, len(cells)):
                years = [re.fullmatch(r"(?:\(\d+\)\s*)?((?:19|20)\d{2})", v)
                         for v in cells[rr][year_cols[0]:year_cols[0] + 3]]
                years = [int(m[1]) for m in years if m]
                if not years:
                    continue
                if len(years) != 1 or years[0] in seen:
                    raise ValueError("MAFF national year ambiguous")
                seen.add(years[0])
                value = cells[rr][col]
                if value in ("", "x", "X", "...", "-"):
                    continue
                amount = float(value.replace(",", ""))
                if not math.isfinite(amount) or amount < 0:
                    raise ValueError("MAFF production invalid")
                out.append(observation(doc, crop, "Japan", years[0], amount / 1e6,
                    basis="grain" if crop == "wheat" else "oilseed", year_basis="crop_year",
                    methodology="MAFF yearbook national production in tonnes; excludes prefectural rows"))
    return out


def parse(doc):
    import xlrd
    workbook = xlrd.open_workbook(file_contents=content(doc))
    out = []
    for sheet in workbook.sheets():
        out.extend(parse_rows([sheet.row_values(r) for r in range(sheet.nrows)], doc))
    if not out:
        raise ValueError("MAFF national wheat/soybean rows missing")
    if len({(r["crop"], r["target_year"]) for r in out}) != len(out):
        raise ValueError("MAFF duplicate national series")
    return {"estimate": out}
