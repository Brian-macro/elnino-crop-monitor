"""Validate v2 evidence. Stale sources warn; integrity violations fail."""

import hashlib
from db import connect
from config import ROOT


def validate_database(con, check_files=True, require_data=True):
    failures = []

    def check(name, ok):
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            failures.append(name)

    if require_data:
        check(
            "production observations exist",
            con.execute("SELECT count(*) FROM production_all").fetchone()[0] > 0,
        )
    for table in (
        "actual_production",
        "forecast_production",
        "estimated_production",
        "climate",
        "prices",
        "futures_prices",
    ):
        check(
            table + " no orphan source document",
            con.execute(
                f"SELECT count(*) FROM {table} p LEFT JOIN source_documents d USING(document_id) WHERE d.document_id IS NULL"
            ).fetchone()[0]
            == 0,
        )
    queries = {
        "actual evidence explicit": "SELECT count(*) FROM actual_production WHERE methodology NOT LIKE 'Official reported actual%'",
        "finite nonnegative production": "SELECT count(*) FROM production_all WHERE value < 0 OR NOT isfinite(value)",
        "metric units compatible": "SELECT count(*) FROM production_all WHERE (metric='yield' AND unit<>'t/ha') OR (metric='area' AND unit<>'Mha') OR (metric NOT IN ('yield','area') AND unit<>'Mt')",
        "rice definitions explicit": "SELECT count(*) FROM production_all WHERE crop='rice' AND commodity_basis NOT IN ('paddy','milled','paddy_early','paddy_semi_late')",
        "no future availability": "SELECT count(*) FROM source_documents WHERE available_date>current_date OR publication_date>current_date",
        "publication precedes availability": "SELECT count(*) FROM source_documents WHERE publication_date>available_date",
        "observation availability matches source": "SELECT count(*) FROM production_all p JOIN source_documents d USING(document_id) WHERE p.available_date<>d.available_date",
        "no duplicate metric within document": "SELECT count(*) FROM (SELECT document_id,crop,country,region,target_year,year_basis,commodity_basis,metric,count(*) n FROM production_all GROUP BY ALL HAVING n>1)",
    }
    for name, query in queries.items():
        check(name, con.execute(query).fetchone()[0] == 0)
    check(
        "futures availability matches archive",
        con.execute(
            "SELECT count(*) FROM futures_prices f JOIN source_documents d USING(document_id) WHERE f.available_date<>d.available_date"
        ).fetchone()[0]
        == 0,
    )
    check(
        "futures exclude incomplete current day",
        con.execute(
            "SELECT count(*) FROM futures_prices WHERE date>=current_date"
        ).fetchone()[0]
        == 0,
    )
    check(
        "domestic usable futures require actual volume",
        con.execute(
            "SELECT count(*) FROM futures_prices WHERE market='china' AND usable AND (volume IS NULL OR volume<=0)"
        ).fetchone()[0]
        == 0,
    )
    if check_files:
        bad = []
        for path, sha in con.execute(
            "SELECT raw_path,sha256 FROM source_documents"
        ).fetchall():
            p = ROOT / path
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
                bad.append(path)
        check("archived raw SHA256 verified", not bad)
        for p in bad:
            print("  " + p)
    return failures


def main():
    con = connect()
    try:
        failures = validate_database(con)
        from research import source_status

        for s in source_status(con):
            print(f"{s['source']}: {s['status']} (age={s['age_days']} days)")
    finally:
        con.close()
    print(f"{len(failures)} hard failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
