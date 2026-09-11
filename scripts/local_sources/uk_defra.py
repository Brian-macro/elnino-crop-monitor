"""DEFRA Agriculture in the UK: harvested wheat and refined sugar."""
import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = "uk_defra"
URL = "https://www.gov.uk/api/content/government/collections/agriculture-in-the-united-kingdom"


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    docs = [d for d in response.json()["links"]["documents"]
            if re.search(r"/agriculture-in-the-united-kingdom-\d{4}$", d["base_path"])]
    if not docs:
        raise ValueError("DEFRA annual publications missing")
    latest = max(docs, key=lambda d: d["base_path"][-4:])
    response = requests.get(latest["api_url"], timeout=(10, 35))
    response.raise_for_status()
    links = [a for a in response.json()["details"]["attachments"] if a["title"] == "Chapter 7: Crops"]
    if len(links) != 1:
        raise ValueError("DEFRA crops chapter missing or ambiguous")
    url = urljoin("https://www.gov.uk", links[0]["url"])
    return [{"url": url.replace("gov.uk/", "gov.uk/api/content/", 1), "suffix": ".json",
             "title": latest["title"] + ": crops", "date_basis": "unknown until chapter metadata is parsed"}]


def resolve_date(payload):
    return {"publication_date": json.loads(payload)["public_updated_at"][:10],
            "date_basis": "GOV.UK chapter public_updated_at; current revised publication"}


def parse(doc):
    soup = BeautifulSoup(json.loads(content(doc))["details"]["body"], "html.parser")
    out = []
    for ident, crop, basis, row_label in [
        ("table-72a", "wheat", "grain", "Volume of harvested production"),
        ("table-76b", "sugar", "refined", "Production"),
    ]:
        heading = soup.find(id=ident)
        if heading is None:
            raise ValueError("DEFRA table missing: " + ident)
        section = heading.find_previous("h3").get_text(" ", strip=True).lower()
        if "thousand tonnes" not in section or ("wheat" if crop == "wheat" else "refined sugar") not in section:
            raise ValueError("DEFRA table definition changed")
        table = heading.find_next("table")
        rows = [[c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])] for row in table.select("tr")]
        years = rows[0][1:]
        if not years or not all(re.fullmatch(r"\d{4}", y) for y in years):
            raise ValueError("DEFRA year columns changed")
        matches = [r[1:] for r in rows if r and r[0] == row_label]
        if len(matches) != 1 or len(matches[0]) != len(years):
            raise ValueError("DEFRA production row ambiguous")
        for year, cell in zip(years, matches[0]):
            if not re.fullmatch(r"\d[\d,]*(?:\.\d+)?", cell):
                raise ValueError("Invalid DEFRA production: " + cell)
            out.append(observation(doc, crop, "United Kingdom", year, float(cell.replace(",", "")) / 1000,
                basis=basis, year_basis="calendar_year", methodology="DEFRA AUK harvested production; sugar refined basis, not raw equivalent"))
    return {"estimate": out}
