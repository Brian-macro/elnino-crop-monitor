"""Research calculations and JSON/API contract; missing data remains None."""

import json, math
from datetime import date, datetime, timezone
import numpy as np
import pandas as pd
from config import COUNTRIES, BASIS, SOURCES, STALE_DAYS


def clean(obj):
    return json.loads(json.dumps(obj, default=str, allow_nan=False))


def records(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))


def asof_rows(rows, asof):
    return [r for r in rows if r["available_date"] <= asof]


def lagged_trend(years, values, window=10):
    out = []
    for i, y in enumerate(years):
        pairs = [
            (x, v)
            for x, v in zip(years[:i], values[:i])
            if y - window <= x < y and v is not None and np.isfinite(v)
        ]
        if len(pairs) < 5:
            out.append(None)
            continue
        xs, vs = zip(*pairs)
        coef = np.polyfit(np.array(xs) - y, vs, 1)
        out.append(float(coef[1]))
    return out


def transform_prices(values, mode):
    valid = [v for v in values if v is not None and math.isfinite(v)]
    if not valid:
        return [None] * len(values)
    base = valid[0]
    mean = float(np.mean(valid))
    sd = float(np.std(valid))
    return [
        (
            None
            if v is None
            else (
                v
                if mode == "raw"
                else (
                    v / base * 100
                    if mode == "indexed" and base
                    else (v - mean) / sd if mode == "standardized" and sd else None
                )
            )
        )
        for v in values
    ]


def strength(v):
    if v <= -0.5:
        return "La Niña range"
    if v < 0.5:
        return "Neutral"
    return (
        "Very strong"
        if v >= 2
        else "Strong" if v >= 1.5 else "Moderate" if v >= 1 else "Weak"
    )


def detect_events(points):
    events = []
    run = []
    prev = None

    def flush():
        if len(run) >= 5:
            peak = max(run, key=lambda r: r["value"])
            events.append(
                dict(
                    id=run[0]["date"][:7],
                    start=run[0]["date"],
                    end=run[-1]["date"],
                    peak=peak["value"],
                    peak_date=peak["date"],
                    seasons=len(run),
                    strength=strength(peak["value"]),
                    start_basis='retrospective first warm-season center month',
                    first_season_period_end=observation_period_end('noaa_oni',run[0]['date']),
                    criterion_met_period_end=observation_period_end('noaa_oni',run[4]['date']),
                    announcement_date=None,
                )
            )

    for p in points:
        dt = date.fromisoformat(p["date"][:10])
        idx = dt.year * 12 + dt.month
        if prev is not None and idx != prev + 1:
            flush()
            run = []
        if p["value"] >= 0.5:
            run.append(p)
        else:
            flush()
            run = []
        prev = idx
    flush()
    return events


def observation_period_end(source, observation):
    if source in ("noaa_oni", "noaa_nino34", "worldbank"):
        return (
            (
                pd.Timestamp(observation)
                + pd.offsets.MonthEnd(2 if source == "noaa_oni" else 1)
            )
            .date()
            .isoformat()
        )
    return observation[:10]


def source_status(con):
    now = datetime.now(timezone.utc)
    stored = {
        r["source"]: r
        for r in records(con.execute("SELECT * FROM source_metadata").fetchdf())
    }
    result = []
    for key, cfg in SOURCES.items():
        r = stored.get(
            key,
            dict(
                source=key,
                status="unavailable",
                error="No validated observations ingested",
                last_checked=None,
                last_success=None,
                last_publication_date=None,
                latest_observation_date=None,
                rows_ingested=0,
            ),
        )
        anchor = (
            r.get("latest_observation_date")
            or r.get("last_publication_date")
            or r.get("last_success")
        )
        effective = (
            observation_period_end(key, anchor)
            if r.get("latest_observation_date")
            else anchor
        )
        age = (
            (now.date() - date.fromisoformat(effective[:10])).days
            if effective
            else None
        )
        if r["status"] in ("ok", "partial") and (age is None or age > STALE_DAYS[key]):
            r["status"] = "stale"
        counts = con.execute(
            "SELECT count(*) FROM production_all WHERE source=?", [key]
        ).fetchone()[0]
        counts += con.execute(
            "SELECT count(*) FROM prices WHERE source=?", [key]
        ).fetchone()[0]
        counts += con.execute(
            "SELECT count(*) FROM climate WHERE source=?", [key]
        ).fetchone()[0]
        counts += con.execute('SELECT count(*) FROM futures_prices WHERE source=?',[key]).fetchone()[0]
        result.append(
            {
                **cfg,
                **r,
                "rows_ingested": counts,
                "age_days": age,
                "stale_after_days": STALE_DAYS[key],
            }
        )
    return result


def climate_bundle(con):
    df = con.execute(
        """SELECT c.*,d.download_timestamp,d.source_url FROM climate c JOIN source_documents d USING(document_id)
       QUALIFY row_number() OVER(PARTITION BY index_name,date ORDER BY c.available_date DESC,d.download_timestamp DESC)=1 ORDER BY date"""
    ).fetchdf()
    series = {}
    for key, g in df.groupby("index_name", sort=False):
        series[key] = records(g)
    summaries = {}
    for key, ps in series.items():
        cur = ps[-1]
        vals = [p["value"] for p in ps]
        duration = 0
        for v in reversed(vals):
            if v >= 0.5:
                duration += 1
            else:
                break
        summaries[key] = {
            **cur,
            "percentile": round(
                sum(v <= cur["value"] for v in vals) / len(vals) * 100, 1
            ),
            "strength": strength(cur["value"]),
            "chg_1m": cur["value"] - vals[-2] if len(vals) > 1 else None,
            "chg_3m": cur["value"] - vals[-4] if len(vals) > 3 else None,
            "warm_seasons": duration,
            "sample_size": len(vals),
        }
    events = detect_events(series.get("ONI", []))
    return dict(
        series=series,
        current=summaries,
        events=events,
        methodology="ONI ERSSTv6: use NOAA published one-decimal table; five consecutive overlapping 3-month seasons >=0.5°C. T is retrospective first-season center, not a real-time declaration. Criterion period end is not announcement date. Current official ENSO diagnosis uses RONI; this is historical ONI comparison.",
        index_version='NOAA ONI ERSSTv6 published table',
        roni_url="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/announcement.php",
    )


def history_rows(latest):
    hist = []
    if "selection_blocked" in latest:
        latest = latest[~latest.selection_blocked.fillna(False).astype(bool)]
    for (source, country, region, basis, ybasis, status), g in latest[
        latest.status.isin(["estimate", "actual"])
    ].groupby(
        ["source", "country", "region", "commodity_basis", "year_basis", "status"]
    ):
        if region or source not in ("usda_psd", "nbs"):
            continue
        pivot = g.pivot_table(
            index="target_year", columns="metric", values="value", aggfunc="last"
        ).sort_index()
        if "production" not in pivot and "yield" not in pivot:
            continue
        years = pivot.index.tolist()
        ys = pivot["yield"].tolist() if "yield" in pivot else [None] * len(years)
        production = (
            pivot["production"].tolist()
            if "production" in pivot
            else [None] * len(years)
        )
        trends = lagged_trend(years, ys)
        ptrends = lagged_trend(years, production)
        prev = {}
        for i, year in enumerate(years):
            p = production[i]
            y = ys[i]
            d = dict(
                country=country,
                region="",
                source=source,
                commodity_basis=basis,
                year_basis=ybasis,
                status=status,
                year=int(year),
                production=p,
                yield_value=y,
                trend_yield=trends[i],
                production_yoy=(
                    (p / prev["p"] - 1) * 100
                    if prev.get("year") == year - 1 and prev.get("p") and p is not None
                    else None
                ),
                yield_yoy=(
                    (y / prev["y"] - 1) * 100
                    if prev.get("year") == year - 1 and prev.get("y") and y is not None
                    else None
                ),
                yield_anomaly=(
                    y - trends[i] if y is not None and trends[i] is not None else None
                ),
                yield_anomaly_pct=(
                    (y / trends[i] - 1) * 100 if y is not None and trends[i] else None
                ),
                production_gap=(
                    (p / ptrends[i] - 1) * 100 if p is not None and ptrends[i] else None
                ),
                available_date=str(g[g.target_year.eq(year)].available_date.max())[:10],
            )
            hist.append(d)
            prev = dict(year=year, p=p, y=y)
    return hist


def crop_bundle(con, crop, asof=None):
    asof = asof or date.today().isoformat()
    df = con.execute(
        """SELECT p.*,d.publication_date_basis FROM production_all p JOIN source_documents d USING(document_id)
      WHERE crop=? AND p.available_date<=? ORDER BY available_date,download_timestamp""",
        [crop, asof],
    ).fetchdf()
    from geography import canonical_country, geography_metadata

    df["source_country"] = df["country"]
    df["country"] = df["country"].map(canonical_country)
    # Full PSD country universe used for derived global histories; disallow EU double-counting.
    psd = df[df.source.eq("usda_psd")].copy()
    keys = [
        "country",
        "region",
        "target_year",
        "year_basis",
        "commodity_basis",
        "metric",
        "source",
        "status",
    ]
    psd = psd.drop_duplicates(["document_id"] + keys, keep="last")
    from normalize import EU_MEMBERS

    global_rows = []
    for _, g in psd.groupby(
        [
            "document_id",
            "source",
            "target_year",
            "year_basis",
            "commodity_basis",
            "metric",
            "status",
        ]
    ):
        metric = g.iloc[0]["metric"]
        if metric == "yield":
            continue
        if "European Union" in set(g.country):
            g = g[~g.country.isin(EU_MEMBERS)]
        r = g.iloc[-1].to_dict()
        r.update(
            country="Global",
            source_country="Derived country aggregate",
            region="",
            value=float(g.value.sum()),
            methodology="Derived sum of full PSD country universe; EU member rows excluded when EU aggregate is present. Not USDA published World total.",
            record_id="derived-" + r["record_id"],
        )
        global_rows.append(r)
    if global_rows:
        df = pd.concat([df, pd.DataFrame(global_rows)], ignore_index=True)
    from regions import aggregate_regions
    from policy import (
        active_countries,
        active_regions,
        annotate_rows,
        geographies,
        research_units,
        POLICY,
    )

    regional = aggregate_regions(df, crop)
    if regional:
        df = pd.concat([df, pd.DataFrame(regional)], ignore_index=True)
    df = df.sort_values(["available_date", "download_timestamp", "record_id"])
    df = df[df.country.isin(active_countries(crop) + active_regions(crop) + ["Global"])]
    # Enforce requested Chinese forecasting source policy, while retaining all source rows in DB.
    df = df[
        ~(
            df.country.eq("China")
            & df.status.eq("forecast")
            & ~df.source.isin(["cropwatch", "china_outlook"])
        )
    ]
    df = annotate_rows(df)
    for optional in [
        "component_records",
        "policy_version",
        "member_count",
        "missing_members",
    ]:
        if optional not in df:
            df[optional] = None
    if "selection_blocked" not in df:
        df["selection_blocked"] = False
    df["selection_blocked"] = df["selection_blocked"].fillna(False).astype(bool)
    prod = df[df.metric.eq("production")].drop_duplicates(
        [
            "document_id",
            "country",
            "region",
            "target_year",
            "year_basis",
            "commodity_basis",
            "status",
        ],
        keep="last",
    )
    fields = [
        "country",
        "source_country",
        "region",
        "target_year",
        "year_basis",
        "commodity_basis",
        "value",
        "source",
        "status",
        "publication_date",
        "available_date",
        "download_timestamp",
        "source_url",
        "methodology",
        "document_id",
        "is_primary",
        "component_records",
        "policy_version",
        "member_count",
        "selection_blocked",
        "missing_members",
    ]
    from outlook import enrich_comparisons, outlook_rows

    production = enrich_comparisons(records(prod[fields]))
    # Latest historical series, same source and basis. PSD current/previous MY remain forecast and excluded from historical estimate series.
    latest = df.drop_duplicates(keys, keep="last")
    hist = history_rows(latest)
    # Latest supply data keyed explicitly by source/year; prices are not inferred from production.
    supply = records(
        latest[
            latest.metric.isin(
                [
                    "beginning_stocks",
                    "ending_stocks",
                    "consumption",
                    "exports",
                    "imports",
                ]
            )
            & (latest.target_year >= 2024)
        ][fields + ["metric"]]
    )
    prices = records(
        con.execute(
            """SELECT p.*,d.source_url,d.download_timestamp FROM prices p JOIN source_documents d USING(document_id)
      WHERE crop=? AND p.available_date<=? QUALIFY row_number() OVER(PARTITION BY p.source,symbol,date ORDER BY p.available_date DESC,d.download_timestamp DESC)=1 ORDER BY date""",
            [crop, asof],
        ).fetchdf()
    )
    for h in hist:
        for key, value in list(h.items()):
            if isinstance(value, float) and not math.isfinite(value):
                h[key] = None
    from analytics import price_research

    return dict(
        crop=crop,
        asof=asof,
        generated_at=datetime.now(timezone.utc).isoformat(),
        production=production,
        history=hist,
        supply=supply,
        prices=prices,
        price_research=price_research(prices),
        geographies=geographies(crop),
        research_units=research_units(crop),
        policy_version=POLICY["version"],
        outlook=outlook_rows(production, date.fromisoformat(asof).year, crop=crop),
        sources=source_status(con),
        regions=sorted({r["region"] for r in production if r["region"]}),
        limitations=[
            "PSD history is latest revised estimate, not final actual and not historical forecast vintage.",
            "Domestic prices: NBS ten-day processing-grade survey. Overseas: World Bank monthly spot/export benchmark. Futures are provided separately in event studies; import parity is not connected.",
            "No interpolation or forecast for missing 2027; source/basis mismatch prevents consensus.",
        ],
    )
