"""Portable typed Parquet exports; immutable originals remain in data/raw."""

from config import PROCESSED
from db import connect


def main():
    con = connect()
    folder = PROCESSED / "parquet"
    folder.mkdir(parents=True, exist_ok=True)
    try:
        for table in (
            "source_documents",
            "actual_production",
            "forecast_production",
            "estimated_production",
            "climate",
            "prices",
            "futures_prices",
            "regions",
            "crop_calendar",
            "source_metadata",
        ):
            path = folder / (table + ".parquet")
            tmp = folder / (table + ".tmp.parquet")
            con.execute(f"COPY {table} TO ? (FORMAT PARQUET)", [str(tmp)])
            tmp.replace(path)
        print("Exported", folder)
    finally:
        con.close()


if __name__ == "__main__":
    main()
