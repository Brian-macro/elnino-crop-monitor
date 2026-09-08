"""PSD normalization: old rows are historical estimates, never asserted as final actuals."""

from datetime import date
import io, zipfile
import pandas as pd
from config import CROPS, BASIS, RAW, PSD_URL
from archive import observation, archive_bytes, content, save_parsed
from db import connect, insert_rows, mark_source

def source_update_month(df):
    if not {'Calendar_Year','Month'}<=set(df.columns):return None
    pairs=[(int(y),int(m)) for y,m in df[['Calendar_Year','Month']].dropna().drop_duplicates().itertuples(index=False,name=None) if 1<=int(m)<=12]
    if not pairs:return None
    year,month=max(pairs)
    return f'{year:04d}-{month:02d}-01'

METRICS = {
    "Production": ("production", "Mt", 1000),
    "Yield": ("yield", "t/ha", 1),
    "Area Harvested": ("area", "Mha", 1000),
    "Beginning Stocks": ("beginning_stocks", "Mt", 1000),
    "Ending Stocks": ("ending_stocks", "Mt", 1000),
    "Domestic Consumption": ("consumption", "Mt", 1000),
    "Domestic Use": ("consumption", "Mt", 1000),
    "Exports": ("exports", "Mt", 1000),
    "Imports": ("imports", "Mt", 1000),
    "Total Disappearance": ("consumption", "Mt", 1000),
}
EU_MEMBERS = {
    "Austria",
    "Belgium",
    "Belgium-Luxembourg",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Poland",
    "Portugal",
    "Romania",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
}


def classify_psd(year, publication_date):
    # Relative to the snapshot, not today's fixed year. Previous MY can still be under harvest/revision.
    return "forecast" if year >= int(str(publication_date)[:4]) - 1 else "estimate"


def ingest_psd(con, doc):
    with zipfile.ZipFile(io.BytesIO(content(doc))) as z:
        name = next(n for n in z.namelist() if n.endswith(".csv"))
        df = pd.read_csv(z.open(name))
    df = df[
        df.Commodity_Description.isin(CROPS) & df.Attribute_Description.isin(METRICS)
    ]
    updated_month=source_update_month(df)
    batches = {"forecast": [], "estimate": []}
    quarantine = []
    for row in df.itertuples():
        crop = CROPS[row.Commodity_Description][0]
        metric, unit, divisor = METRICS[row.Attribute_Description]
        if (
            metric not in ("yield", "area")
            and row.Unit_Description.strip() != "(1000 MT)"
        ):
            raise ValueError(f"Unexpected PSD unit: {row.Unit_Description}")
        if pd.isna(row.Value):
            continue
        if row.Value < 0:
            quarantine.append(
                {
                    "crop": crop,
                    "country": row.Country_Name,
                    "year": row.Market_Year,
                    "metric": metric,
                    "value": row.Value,
                    "reason": "negative official value; excluded from analytical series",
                }
            )
            continue
        kind = classify_psd(row.Market_Year, doc["available_date"])
        r = observation(
            doc,
            crop,
            row.Country_Name,
            row.Market_Year,
            row.Value / divisor,
            metric,
            unit,
            BASIS[crop],
            methodology="USDA PSD snapshot; source attribute: "
            + row.Attribute_Description
            + "; historical values are revised estimates; current/previous MY are forecast/estimate, not final actual",
        )
        # Rice PSD yield refers to rough rice; never combine with milled production yield.
        if crop == "rice" and metric == "yield":
            r["commodity_basis"] = "paddy"
        batches[kind].append(r)
    con.execute("BEGIN")
    try:
        for kind, rows in batches.items():
            insert_rows(con, rows, kind)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    # Country universe remains intact; PSD global figures are explicitly derived country sums.
    if quarantine:
        save_parsed(doc, {"quarantined": quarantine})
    mark_source(
        con,
        "usda_psd",
        True,
        doc["publication_date"],
        rows=sum(map(len, batches.values())),
        status="partial" if quarantine else "ok",
        error=(
            f"{len(quarantine)} negative source rows quarantined; raw retained"
            if quarantine
            else None
        ),
        observation_date=updated_month,
    )
    print("PSD normalized", {k: len(v) for k, v in batches.items()})


def main():
    con = connect()
    # Explicit bootstrap: archive the existing genuine binary without trusting filename as publication evidence.
    for p in sorted((RAW / "usda").glob("psd_alldata_*.zip")):
        doc = archive_bytes(
            con,
            "usda_psd",
            PSD_URL,
            p.read_bytes(),
            ".zip",
            title="Legacy PSD snapshot; publication date unverified",
        )
        ingest_psd(con, doc)
    con.close()


if __name__ == "__main__":
    main()
