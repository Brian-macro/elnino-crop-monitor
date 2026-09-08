"""Append-only research store. Legacy monitor.duckdb is preserved."""

import hashlib
import json
import duckdb
from config import DB_PATH, ROOT

COLUMNS = """record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL,
 crop VARCHAR NOT NULL, country VARCHAR NOT NULL, region VARCHAR NOT NULL DEFAULT '',
 target_year INTEGER NOT NULL, year_basis VARCHAR NOT NULL, commodity_basis VARCHAR NOT NULL,
 metric VARCHAR NOT NULL, value DOUBLE NOT NULL CHECK(isfinite(value) AND value >= 0), unit VARCHAR NOT NULL,
 source VARCHAR NOT NULL, publication_date DATE, available_date DATE NOT NULL,
 download_timestamp TIMESTAMP NOT NULL, methodology VARCHAR NOT NULL, source_url VARCHAR NOT NULL"""
DDL = f"""
CREATE TABLE IF NOT EXISTS source_documents (
 document_id VARCHAR PRIMARY KEY, source VARCHAR, source_url VARCHAR, raw_path VARCHAR,
 sha256 VARCHAR, publication_date DATE, available_date DATE, download_timestamp TIMESTAMP,
 publication_date_basis VARCHAR, title VARCHAR, UNIQUE(source, source_url, sha256));
CREATE TABLE IF NOT EXISTS actual_production ({COLUMNS});
CREATE TABLE IF NOT EXISTS forecast_production ({COLUMNS});
CREATE TABLE IF NOT EXISTS estimated_production ({COLUMNS});
CREATE TABLE IF NOT EXISTS climate (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR, index_name VARCHAR, date DATE,
 season VARCHAR, value DOUBLE, unit VARCHAR, source VARCHAR, available_date DATE);
CREATE TABLE IF NOT EXISTS prices (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR, crop VARCHAR, market VARCHAR,
 symbol VARCHAR, date DATE, value DOUBLE CHECK(value > 0), currency VARCHAR, unit VARCHAR,
 price_type VARCHAR, source VARCHAR, available_date DATE);
CREATE TABLE IF NOT EXISTS futures_prices (
 record_id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL, series_id VARCHAR NOT NULL,
 crop VARCHAR, market VARCHAR, symbol VARCHAR, date DATE,
 open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE CHECK(isfinite(close) AND close > 0),
 volume DOUBLE, open_interest DOUBLE, settlement DOUBLE, usable BOOLEAN,
 currency VARCHAR, unit VARCHAR, commodity_basis VARCHAR, source VARCHAR,
 available_date DATE, roll_method VARCHAR);
CREATE TABLE IF NOT EXISTS regions (
 country VARCHAR, region VARCHAR, parent_region VARCHAR, latitude DOUBLE, longitude DOUBLE,
 source_url VARCHAR, PRIMARY KEY(country,region));
CREATE TABLE IF NOT EXISTS crop_calendar (
 crop VARCHAR, country VARCHAR, region VARCHAR, stage VARCHAR, start_month INTEGER,
 end_month INTEGER, source_url VARCHAR, publication_date DATE);
CREATE TABLE IF NOT EXISTS source_metadata (
 source VARCHAR PRIMARY KEY, last_checked TIMESTAMP, last_success TIMESTAMP,
 last_publication_date DATE, latest_observation_date DATE, status VARCHAR, error VARCHAR,
 rows_ingested BIGINT DEFAULT 0);
CREATE VIEW IF NOT EXISTS production_all AS
 SELECT *, 'actual' AS status FROM actual_production UNION ALL
 SELECT *, 'forecast' AS status FROM forecast_production UNION ALL
 SELECT *, 'estimate' AS status FROM estimated_production;
CREATE VIEW IF NOT EXISTS forecast_vintage AS
 SELECT *, available_date AS forecast_date, value AS forecast_value,
 DENSE_RANK() OVER (PARTITION BY crop,country,region,target_year,source,year_basis,commodity_basis,metric
 ORDER BY available_date,download_timestamp,document_id) AS revision_number
 FROM forecast_production;
"""


def connect(path=None):
    con = duckdb.connect(str(path or DB_PATH))
    con.execute(DDL)
    return con


def mark_source(
    con,
    source,
    ok,
    pub_date=None,
    error=None,
    observation_date=None,
    rows=0,
    status=None,
):
    import os

    if os.environ.get("MONITOR_OFFLINE") == "1":
        if not con.execute(
            "SELECT 1 FROM source_metadata WHERE source=?", [source]
        ).fetchone():
            con.execute(
                "INSERT INTO source_metadata(source,status,error,rows_ingested) VALUES (?,'partial','Offline archive replay; no live source check',?)",
                [source, rows],
            )
        return
    con.execute(
        """INSERT INTO source_metadata VALUES (?,now(),CASE WHEN ? THEN now() END,?,?,?,?,?)
      ON CONFLICT(source) DO UPDATE SET last_checked=now(),
      last_success=CASE WHEN ? THEN now() ELSE source_metadata.last_success END,
      last_publication_date=coalesce(excluded.last_publication_date,source_metadata.last_publication_date),
      latest_observation_date=coalesce(excluded.latest_observation_date,source_metadata.latest_observation_date),
      status=excluded.status,error=excluded.error,rows_ingested=CASE WHEN ? THEN excluded.rows_ingested ELSE source_metadata.rows_ingested END""",
        [
            source,
            ok,
            pub_date,
            observation_date,
            status or ("ok" if ok else "stale"),
            error,
            rows,
            ok,
            ok,
        ],
    )


def insert_rows(con, rows, status):
    if not rows:
        return 0
    import pandas as pd

    table = {
        "forecast": "forecast_production",
        "estimate": "estimated_production",
        "actual": "actual_production",
    }[status]
    for r in rows:
        if status == "actual" and not r.get("methodology", "").startswith(
            "Official reported actual"
        ):
            raise ValueError("Actual requires explicit official final-output evidence")
        identity = [
            r[k]
            for k in (
                "document_id",
                "crop",
                "country",
                "region",
                "target_year",
                "year_basis",
                "commodity_basis",
                "metric",
            )
        ]
        r["record_id"] = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    con.register("_incoming", pd.DataFrame(rows))
    con.execute(
        f"INSERT INTO {table} BY NAME SELECT * FROM _incoming ON CONFLICT DO NOTHING"
    )
    con.unregister("_incoming")
    return len(rows)


if __name__ == "__main__":
    connect().close()
    (ROOT / "docs" / "schema.sql").write_text(DDL, encoding="utf-8")
    print(DB_PATH)
