"""AFA historical paddy production by rice type and cropping season."""
import json
import math
from archive import content, observation

SOURCE = "tw_afa"
URL = "https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=dONVIzvBlFbw"
TYPES = {"\u9577\u7cef", "\u5713\u7cef", "\u79c8\u7a3b", "\u5728\u4f86", "\u84ec\u840a"}


def discover():
    return [{"url": URL, "suffix": ".json", "title": "AFA rice production by type (paddy)",
             "date_basis": "unknown payload revision date; first observed; discontinued historical dataset"}]


def parse(doc):
    records = json.loads(content(doc))
    if not isinstance(records, list):
        raise ValueError("AFA expected record array")
    years = {}
    for row in records:
        if not {"year", "plant_time", "type", "yield"}.issubset(row):
            raise ValueError("AFA schema changed")
        year, season = int(row["year"]), int(row["plant_time"])
        if year < 1900 or year > 2100 or season not in (1, 2) or row["type"] not in TYPES:
            raise ValueError("AFA year/season/type changed")
        group = years.setdefault(year, {})
        key = (season, row["type"])
        if key in group:
            raise ValueError("AFA duplicate season/type")
        group[key] = row["yield"]
    expected = {(s, t) for s in (1, 2) for t in TYPES}
    out = []
    for year, group in sorted(years.items()):
        if set(group) != expected or any(v is None or v == "" for v in group.values()):
            continue
        values = [float(v) for v in group.values()]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("AFA invalid tonnes")
        out.append(observation(doc, "rice", "Taiwan", year, sum(values) / 1e6,
            basis="paddy", year_basis="calendar_year", methodology="AFA paddy metric tonnes; complete 5 rice types x 2 seasons; no milling conversion"))
    if not out:
        raise ValueError("AFA no complete annual production")
    return {"estimate": out}
