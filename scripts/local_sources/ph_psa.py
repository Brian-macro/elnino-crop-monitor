"""PSA OpenSTAT annual palay and corn. POST transport must be honored.

discover/parse match the local-source contract, but the existing GET-only
orchestrator must use fetch(item) and archive its bytes before parse(doc).
"""
import csv
import io
import math
import re
from datetime import date

import requests
from archive import content, observation

SOURCE = "ph_psa"
URL = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2E/CS/0012E4EVCP0.px"


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    metadata = response.json()
    if "Volume of Production in Metric Tons" not in metadata["title"]:
        raise ValueError("PSA table definition changed")
    selections = {"Ecosystem/Croptype": {"Palay", "Corn"}, "Geolocation": {"PHILIPPINES"}, "Period": {"Annual"}}
    if {v["code"] for v in metadata["variables"]} != set(selections) | {"Year"}:
        raise ValueError("PSA dimensions changed")
    query = []
    for variable in metadata["variables"]:
        code = variable["code"]
        mapping = dict(zip(variable["valueTexts"], variable["values"]))
        wanted = selections.get(code, set(mapping))
        if not wanted.issubset(mapping):
            raise ValueError("PSA national annual selections missing")
        query.append({"code": code, "selection": {"filter": "item", "values": [mapping[k] for k in mapping if k in wanted]}})
    return [{"url": URL, "method": "POST", "json": {"query": query, "response": {"format": "csv"}},
             "suffix": ".csv", "title": metadata["title"],
             "date_basis": "unknown PSA vintage date; query response updated timestamp is not publication evidence"}]


def fetch(item):
    response = requests.post(item["url"], json=item["json"], timeout=(10, 35))
    response.raise_for_status()
    return response.content


def parse(doc):
    reader = csv.DictReader(io.StringIO(content(doc).decode("utf-8-sig")))
    fields = reader.fieldnames or []
    if fields[:2] != ["Ecosystem/Croptype", "Geolocation"] or len(fields) < 3:
        raise ValueError("PSA CSV schema changed; archive POST CSV, not GET metadata")
    if any(not re.fullmatch(r"\d{4} Annual", f) for f in fields[2:]) or len(set(fields)) != len(fields):
        raise ValueError("PSA annual columns changed")
    out, seen = [], set()
    for row in reader:
        label = row[fields[0]]
        if row[fields[1]] != "PHILIPPINES" or label not in ("Palay", "Corn") or label in seen:
            raise ValueError("PSA expected unique national crop totals")
        seen.add(label)
        for field in fields[2:]:
            year = int(field[:4])
            # An Annual cell for a still-open calendar year may be year-to-date.
            if year >= date.fromisoformat(str(doc["available_date"])[:10]).year:
                continue
            cell = row[field].strip()
            if cell in ("", "..", "...", "-", "NA"):
                continue
            value = float(cell.replace(",", ""))
            if not math.isfinite(value) or value < 0:
                raise ValueError("PSA invalid production")
            out.append(observation(doc, "rice" if label == "Palay" else "corn", "Philippines", year, value / 1e6,
                basis="paddy" if label == "Palay" else "grain", year_basis="calendar_year",
                methodology="PSA national Annual cell, metric tonnes; closed years only; provisional/revised estimates"))
    if seen != {"Palay", "Corn"} or not out:
        raise ValueError("PSA annual production incomplete")
    return {"estimate": out}
