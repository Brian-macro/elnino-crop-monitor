import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from db import connect, insert_rows
from event_study import balance_rows


def test_event_balance_uses_same_year_document_and_no_china_policy_filter():
    c = connect(":memory:")
    for doc, when in [("old", "2026-07-10"), ("new", "2026-08-12")]:
        c.execute(
            "INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                doc,
                "usda_psd",
                "https://example.org/" + doc,
                "data/raw/test",
                doc,
                None,
                when,
                when,
                "fixture",
                "fixture",
            ],
        )
    rows = []
    for doc, when in [("old", "2026-07-10"), ("new", "2026-08-12")]:
        for country, p, stocks, use in [
            ("China", 100, 20, 80),
            ("United States", 50, 10, 40),
        ]:
            for metric, value in [
                ("production", p),
                ("ending_stocks", stocks),
                ("consumption", use),
            ]:
                if doc == "new" and country == "China" and metric == "ending_stocks":
                    continue
                rows.append(
                    dict(
                        document_id=doc,
                        crop="corn",
                        country=country,
                        region="",
                        target_year=2026,
                        year_basis="marketing_year",
                        commodity_basis="grain",
                        metric=metric,
                        value=value,
                        unit="Mt",
                        source="usda_psd",
                        publication_date=None,
                        available_date=when,
                        download_timestamp=when,
                        methodology="fixture",
                        source_url="https://example.org/" + doc,
                    )
                )
    insert_rows(c, rows, "forecast")
    result = balance_rows(c, "corn")["usda_psd"]["2026"]
    assert result["China"]["production"] == 100
    assert result["China"]["ending_stocks"] is None
    assert result["China"]["stocks_to_use"] is None
    assert result["Global"]["production"] == 150
    assert result["Global"]["ending_stocks"] is None
    assert result["China"]["document_id"] == "new"
    c.close()


def test_sugar_inventory_denominator_uses_total_domestic_disappearance(monkeypatch):
    import io, zipfile
    import normalize

    csv = "Commodity_Description,Country_Name,Market_Year,Attribute_Description,Unit_Description,Value\n"
    for metric, value in [
        ("Production", 10000),
        ("Human Dom. Consumption", 15000),
        ("Other Disappearance", 100),
        ("Total Disappearance", 15100),
        ("Ending Stocks", 1510),
    ]:
        csv += f'"Sugar, Centrifugal",China,2023,{metric},(1000 MT),{value}\n'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        z.writestr("psd.csv", csv)
    monkeypatch.setattr(normalize, "content", lambda doc: stream.getvalue())
    c = connect(":memory:")
    doc = dict(
        document_id="sugar",
        source="usda_psd",
        publication_date=None,
        available_date="2026-08-12",
        download_timestamp="2026-08-12",
        source_url="https://example.org/sugar",
    )
    normalize.ingest_psd(c, doc)
    value = c.execute(
        "SELECT value FROM estimated_production WHERE crop='sugar' AND metric='consumption'"
    ).fetchone()[0]
    assert value == 15.1
    assert (
        c.execute(
            "SELECT count(*) FROM estimated_production WHERE metric='consumption'"
        ).fetchone()[0]
        == 1
    )
    c.close()
