"""US-only NASS Crop Production reports, using their official metric table."""
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = "us_nass"
URL = "https://esmis.nal.usda.gov/publication/crop-production"


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    links = BeautifulSoup(response.content, "html.parser").select('a[href$=".txt"]')
    candidates = sorted({urljoin(URL, a["href"]) for a in links
                         if re.search(r"/crop\d{4}\.txt$", a["href"])},
                        key=lambda u: (u[-6:-4], u[-8:-6]), reverse=True)
    if not candidates:
        raise ValueError("NASS report text links missing")
    return [{"url": candidates[0], "suffix": ".txt", "title": "NASS Crop Production",
             "date_basis": "unknown until official release line is parsed"}]


def resolve_date(payload):
    match = re.search(r"Released\s+([A-Za-z]+ \d{1,2}, \d{4}), by", payload.decode("latin-1"))
    if not match:
        raise ValueError("NASS release date missing")
    return {"publication_date": datetime.strptime(match[1], "%B %d, %Y").date().isoformat(),
            "date_basis": "official NASS Released line"}


def parse(doc):
    text = content(doc).decode("latin-1").replace("\r", "")
    blocks = re.split(r"Crop Area Planted and Harvested, Yield, and Production in Metric Units - United States:\s*", text)[1:]
    out = {"forecast": [], "estimate": []}
    crops = {"Corn for grain": ("corn", "grain"), "Wheat, all": ("wheat", "grain"),
             "Rice": ("rice", "paddy"), "Soybeans for beans": ("soybean", "oilseed")}
    seen = set()
    for block in blocks:
        if not re.match(r"\d{4} and \d{4}", block):
            continue
        lines = block.splitlines()
        header = next((i for i, line in enumerate(lines) if "Yield per hectare" in line and "Production" in line), None)
        if header is None:
            continue
        if not any("metric tons" in line for line in lines[header:header + 14]):
            raise ValueError("NASS production unit changed")
        year_line = next(line for line in lines[header + 1:] if len(re.findall(r"\b\d{4}\b", line)) == 4)
        years = [int(y) for y in re.findall(r"\b\d{4}\b", year_line)]
        boundaries = [m.start() for m in re.finditer(":", year_line)]
        if len(boundaries) != 4 or years[:2] != years[2:]:
            raise ValueError("NASS year columns changed")
        unit_row = next(i for i in range(header, len(lines)) if "metric tons" in lines[i])
        for line in lines[unit_row + 1:]:
            if re.fullmatch(r"-+", line.strip()):
                break
            if ":" not in line:
                continue
            label = re.sub(r"\s+\d+/", "", line.split(":", 1)[0]).rstrip(". ")
            if label not in crops:
                continue
            crop, basis = crops[label]
            for j, year in enumerate(years[2:]):
                start = boundaries[2 + j] + 1
                end = boundaries[3] + 1 if j == 0 else len(line)
                cell = line[start:end].strip()
                if cell in ("", "(NA)", "(X)"):
                    continue
                if not re.fullmatch(r"\d[\d,]*(?:\.\d+)?", cell):
                    raise ValueError("Invalid NASS production cell: " + cell)
                if (crop, year) in seen:
                    raise ValueError("Duplicate NASS production")
                seen.add((crop, year))
                status = "forecast" if year == int(str(doc["publication_date"])[:4]) else "estimate"
                out[status].append(observation(doc, crop, "United States", year,
                    float(cell.replace(",", "")) / 1e6, basis=basis, year_basis="crop_year",
                    methodology="NASS national metric table; rice is rough rice; latest report estimates"))
    if not seen:
        raise ValueError("NASS metric production table missing")
    return out
