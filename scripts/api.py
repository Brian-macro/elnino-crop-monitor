"""Optional read-only query API. Static JSON endpoints need no Python server."""

from datetime import date
from pathlib import Path
from typing import Literal
import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from config import DB_PATH, ROOT, CROPS
from research import crop_bundle, climate_bundle, source_status, records
from geography import canonical_country, ALIASES
from outlook import outlook_rows
from policy import active_countries, policy_bundle
from event_study import event_bundle

app = FastAPI(title="El Nino Crop Monitor", version="0.2.0")
CROP_NAMES = {slug for slug, _ in CROPS.values()}


def connection():
    try:
        return duckdb.connect(str(DB_PATH), read_only=True)
    except duckdb.Error as e:
        raise HTTPException(
            503, "Database unavailable or updating; retry shortly"
        ) from e


@app.get("/health")
def health():
    with connection() as con:
        return dict(
            status="ok",
            documents=con.execute("SELECT count(*) FROM source_documents").fetchone()[
                0
            ],
        )


@app.get("/api/sources")
def sources():
    with connection() as con:
        return dict(
            sources=source_status(con),
            documents=records(
                con.execute(
                    "SELECT * FROM source_documents ORDER BY download_timestamp DESC"
                ).fetchdf()
            ),
        )


@app.get("/api/climate")
def climate():
    with connection() as con:
        return climate_bundle(con)


@app.get("/api/policy")
def policy():
    return policy_bundle()


@app.get("/api/events/{crop}")
def events(crop: str):
    if crop not in CROP_NAMES:
        raise HTTPException(404, "Unknown crop")
    with connection() as con:
        return event_bundle(con, crop)


@app.get("/api/crops/{crop}")
def crops(crop: str, asof: date | None = None):
    if crop not in CROP_NAMES:
        raise HTTPException(404, "Unknown crop")
    if asof and asof > date.today():
        raise HTTPException(422, "asof cannot be in the future")
    with connection() as con:
        return crop_bundle(con, crop, asof.isoformat() if asof else None)


@app.get("/api/outlook/{crop}")
def outlook(
    crop: str,
    target_year: int | None = None,
    status: Literal["actual", "forecast", "estimate"] = "forecast",
    source: str = "auto",
    baseline: Literal["reported", "estimate", "actual"] = "reported",
    subregion: Literal["East Asia", "Southeast Asia"] | None = None,
    asof: date | None = None,
    view: Literal["regions", "countries"] = "regions",
):
    if crop not in CROP_NAMES:
        raise HTTPException(404, "Unknown crop")
    if asof and asof > date.today():
        raise HTTPException(422, "asof cannot be in the future")
    effective = asof or date.today()
    target_year = target_year or effective.year
    with connection() as con:
        bundle = crop_bundle(con, crop, effective.isoformat())
    rows = outlook_rows(
        bundle["production"],
        target_year,
        status,
        source,
        baseline,
        subregion,
        crop=crop,
    )
    rows = (
        [r for r in rows if r["country"] in bundle["research_units"]]
        if view == "regions"
        else [r for r in rows if r["level"] != "region"]
    )
    return dict(
        crop=crop,
        target_year=target_year,
        asof=effective,
        baseline=baseline,
        rows=rows,
        coverage=dict(
            countries=len(rows),
            with_production=sum(r["production"] is not None for r in rows),
            with_yoy=sum(r["yoy"] is not None for r in rows),
        ),
    )


@app.get("/api/production")
def production(
    crop: str,
    country: str | None = None,
    region: str | None = None,
    target_year: int | None = None,
    source: str | None = None,
    status: Literal["actual", "forecast", "estimate"] | None = None,
    year_basis: Literal["calendar_year", "marketing_year"] | None = None,
    commodity_basis: str | None = None,
    metric: str = "production",
    asof: date | None = None,
    limit: int = Query(5000, ge=1, le=50000),
):
    if crop not in CROP_NAMES:
        raise HTTPException(404, "Unknown crop")
    if asof and asof > date.today():
        raise HTTPException(422, "asof cannot be in the future")
    allowed = active_countries(crop) + ["Global"]
    aliases = [key for key, value in ALIASES.items() if value in allowed]
    conditions = [
        "crop=?",
        "available_date<=?",
        "metric=?",
        "country=ANY(?)",
    ]
    args = [crop, asof or date.today(), metric, allowed + aliases]
    if country:
        canonical = canonical_country(country)
        matches = [canonical] + [
            alias for alias, value in ALIASES.items() if value == canonical
        ]
        conditions.append("country=ANY(?)")
        args.append(matches)
    for key, value in [
        ("region", region),
        ("target_year", target_year),
        ("source", source),
        ("status", status),
        ("year_basis", year_basis),
        ("commodity_basis", commodity_basis),
    ]:
        if value is not None:
            conditions.append(key + "=?")
            args.append(value)
    with connection() as con:
        rows = records(
            con.execute(
                "SELECT * FROM production_all WHERE "
                + " AND ".join(conditions)
                + " ORDER BY available_date DESC,download_timestamp DESC LIMIT ?",
                args + [limit],
            ).fetchdf()
        )
    return dict(rows=rows, asof=asof or date.today(), limit=limit)


@app.get("/api/documents/{document_id}/raw")
def raw_document(document_id: str):
    with connection() as con:
        r = con.execute(
            "SELECT raw_path FROM source_documents WHERE document_id=?", [document_id]
        ).fetchone()
    if not r:
        raise HTTPException(404, "Unknown source document")
    p = (ROOT / r[0]).resolve()
    if not p.is_relative_to((ROOT / "data" / "raw").resolve()) or not p.is_file():
        raise HTTPException(404, "Archive unavailable")
    return FileResponse(p, filename=p.name)
