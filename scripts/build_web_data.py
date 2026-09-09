"""Publish validated DuckDB data as atomic JSON files consumed by Next and static API."""

import json, os
from datetime import datetime, timezone
from config import WEB, ROOT, CROPS
from db import connect
from research import crop_bundle, climate_bundle, source_status, records
from policy import policy_bundle
from outlook import preferred
from dashboard import dashboard_bundle
from event_study import event_bundle


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"), default=str
        ),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def main():
    con = connect()
    summary = {}
    coverage = []
    climate = climate_bundle(con)
    con.execute(
        """INSERT INTO regions(country,region,parent_region,source_url)
      SELECT country,region,CASE WHEN region='' THEN 'Global' ELSE country END,source_url FROM production_all
      QUALIFY row_number() OVER(PARTITION BY country,region ORDER BY available_date DESC)=1
      ON CONFLICT DO NOTHING"""
    )
    for crop, _ in CROPS.values():
        dashboard = dashboard_bundle(con, crop)
        event_data = event_bundle(con, crop, climate, dashboard=dashboard)
        dump(WEB / ("events_" + crop + ".json"), event_data)
        dump(ROOT / "public" / "api" / ("events_" + crop + ".json"), event_data)
        dump(WEB / ("dashboard_" + crop + ".json"), dashboard)
        dump(ROOT / "public" / "api" / ("dashboard_" + crop + ".json"), dashboard)
        bundle = crop_bundle(con, crop)
        dump(WEB / (crop + ".json"), bundle)
        dump(ROOT / "public" / "api" / (crop + ".json"), bundle)
        print(
            crop,
            len(bundle["production"]),
            len(bundle["history"]),
            len(bundle["prices"]),
        )
        for row in bundle["outlook"]:
            if row["subregion"] not in ("East Asia", "Southeast Asia"):
                continue
            current = row["production"]
            previous = row["previous"]
            coverage.append(
                dict(
                    crop=crop,
                    country=row["country"],
                    subregion=row["subregion"],
                    map_name=row["map_name"],
                    target_year=datetime.now().year,
                    production=current["value"] if current else None,
                    source=current["source"] if current else None,
                    status=current["status"] if current else None,
                    commodity_basis=current["commodity_basis"] if current else None,
                    year_basis=current["year_basis"] if current else None,
                    previous_value=previous["value"] if previous else None,
                    previous_status=previous["status"] if previous else None,
                    yoy=row["yoy"],
                    reason=row["reason"],
                    source_url=current["source_url"] if current else None,
                    available_date=current["available_date"] if current else None,
                )
            )
        rs = [
            r
            for r in bundle["production"]
            if r["country"] == "Global"
            and r["target_year"] == datetime.now().year
            and r["status"] == "forecast"
        ]
        summary[crop] = preferred(rs, "Global")
    climate = climate_bundle(con)
    sources = source_status(con)
    docs = records(
        con.execute(
            "SELECT * FROM source_documents ORDER BY download_timestamp DESC"
        ).fetchdf()
    )
    for name, obj in [
        ("elnino", climate),
        ("sources", dict(sources=sources, documents=docs)),
        (
            "overview",
            dict(
                updated=datetime.now(timezone.utc).isoformat(),
                crops=summary,
                climate=climate["current"],
                sources=sources,
            ),
        ),
    ]:
        dump(WEB / (name + ".json"), obj)
        dump(ROOT / "public" / "api" / (name + ".json"), obj)
    report = dict(
        generated_at=datetime.now(timezone.utc).isoformat(),
        baseline="reported",
        rows=coverage,
    )
    dump(WEB / "asia_coverage.json", report)
    dump(ROOT / "public" / "api" / "asia_coverage.json", report)
    policy = policy_bundle()
    dump(WEB / "policy.json", policy)
    dump(ROOT / "public" / "api" / "policy.json", policy)
    con.close()


if __name__ == "__main__":
    main()
