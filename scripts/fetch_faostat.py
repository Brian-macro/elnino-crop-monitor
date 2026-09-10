"""FAOSTAT annual official production for historical event review."""

import csv
import io
import zipfile

from archive import content, download, failed, observation, save_parsed
from db import connect, insert_rows, mark_source

FAOSTAT_URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
ITEMS = {
    "Wheat": ("wheat", "grain"),
    "Maize (corn)": ("corn", "grain"),
    "Rice": ("rice", "paddy"),
    "Soya beans": ("soybean", "oilseed"),
}
AREAS = {"World": "Global", "China": "China"}


def parse_actuals(csv_text, doc):
    rows = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        if (
            row.get("Element") != "Production"
            or row.get("Flag") != "A"
            or row.get("Item") not in ITEMS
            or row.get("Area") not in AREAS
            or row.get("Unit") != "t"
        ):
            continue
        crop, basis = ITEMS[row["Item"]]
        rows.append(
            observation(
                doc,
                crop,
                AREAS[row["Area"]],
                int(row["Year"]),
                float(row["Value"]) / 1_000_000,
                unit="Mt",
                basis=basis,
                year_basis="calendar_year",
                methodology="Official reported actual: FAOSTAT annual production database; flag A official data",
            )
        )
    return rows


def main():
    con = connect()
    try:
        doc = download(
            con,
            "faostat",
            FAOSTAT_URL,
            suffix=".zip",
            title="FAOSTAT Crops and livestock products annual production database",
            date_basis="FAOSTAT official bulk download; first observed",
        )
        with zipfile.ZipFile(io.BytesIO(content(doc))) as archive:
            member = next(
                name
                for name in archive.namelist()
                if name.endswith(".csv") and "Normalized" in name
            )
            with archive.open(member) as raw:
                rows = parse_actuals(raw.read().decode("utf-8-sig"), doc)
        if not rows:
            raise ValueError("FAOSTAT file contains no official target production rows")
        save_parsed(doc, rows)
        insert_rows(con, rows, "actual")
        mark_source(
            con,
            "faostat",
            True,
            rows=len(rows),
            status="partial",
            error="Sugar is excluded: FAOSTAT World/China raw sugar records are estimated (flag E), not official actuals.",
        )
        print("FAOSTAT", len(rows), "official actual production rows")
    except Exception as error:
        failed(con, "faostat", error)
        return 2
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
