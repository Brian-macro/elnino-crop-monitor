"""Restore a new DuckDB from portable exports; refuse to overwrite an existing database."""

import argparse
from pathlib import Path
from config import PROCESSED
from db import connect
from validate import validate_database


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    target = Path(args.db)
    if target.exists():
        raise SystemExit("Refusing to overwrite existing database: " + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    con = connect(target)
    try:
        con.execute("BEGIN")
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
            p = PROCESSED / "parquet" / (table + ".parquet")
            if not p.exists():
                raise ValueError("Missing portable export " + str(p))
            con.execute(
                f"INSERT INTO {table} BY NAME SELECT * FROM read_parquet(?)", [str(p)]
            )
        failures = validate_database(con)
        if failures:
            raise ValueError("Invalid source exports: " + str(failures))
        con.execute("COMMIT")
        print("Restored", target)
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()
