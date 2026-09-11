"""DOSM/DOA national paddy production, in metric tonnes, not million tonnes."""
import csv
import io
import math
from datetime import date
from archive import content, observation

SOURCE = "my_dosm"
URL = "https://storage.data.gov.my/agriculture/crops_state.csv"


def discover():
    return [{"url": URL, "suffix": ".csv", "title": "DOSM Crop Area and Production by State",
             "date_basis": "unknown CSV revision date; first observed (catalogue last updated 2023-12-31)"}]


def parse(doc):
    reader = csv.DictReader(io.StringIO(content(doc).decode("utf-8-sig")))
    if not {"state", "date", "crop_type", "production"}.issubset(reader.fieldnames or []):
        raise ValueError("DOSM CSV schema changed")
    out, seen = [], set()
    for row in reader:
        if row["state"] != "Malaysia" or row["crop_type"] != "paddy":
            continue
        day = date.fromisoformat(row["date"])
        if (day.month, day.day) != (1, 1) or day.year in seen:
            raise ValueError("DOSM annual key invalid or duplicated")
        seen.add(day.year)
        if row["production"].strip() in ("", "NA", "null"):
            continue
        value = float(row["production"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("DOSM invalid production")
        out.append(observation(doc, "rice", "Malaysia", day.year, value / 1e6,
            basis="paddy", year_basis="calendar_year", methodology="DOSM/DOA national total, metric tonnes; no state summation or milling conversion"))
    if not out:
        raise ValueError("DOSM national paddy rows missing")
    return {"estimate": out}
