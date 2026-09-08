"""Auditable production comparisons; source classifications and missing values stay explicit."""

from collections import defaultdict
from policy import primary_source, geographies


def definition(row):
    return tuple(row[k] for k in ("country", "region", "year_basis", "commodity_basis"))


def latest(rows):
    return max(
        rows,
        key=lambda r: (
            str(r["available_date"])[:10],
            str(r["download_timestamp"]),
            r["document_id"],
        ),
        default=None,
    )


def preferred(rows, country, source="auto"):
    rows = [r for r in rows if not r.get("selection_blocked")]
    if source != "auto":
        rows = [r for r in rows if r["source"] == source]
    whole = [
        r
        for r in rows
        if r["commodity_basis"]
        not in ("paddy_early", "paddy_semi_late", "winter_wheat")
    ]
    rows = whole or rows
    if source != "auto":
        return latest(rows)
    return latest(
        [
            r
            for r in rows
            if r.get(
                "is_primary",
                r["source"]
                == primary_source(
                    country, r["status"], r["target_year"], r["available_date"]
                ),
            )
        ]
    )


REFERENCE_FIELDS = (
    "country",
    "region",
    "target_year",
    "year_basis",
    "commodity_basis",
    "source",
    "status",
    "value",
    "available_date",
    "publication_date",
    "download_timestamp",
    "document_id",
    "source_url",
    "methodology",
)


def enrich_comparisons(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(definition(r), r["target_year"])].append(r)
    result = []
    for r in rows:
        candidates = [
            p
            for p in groups.get((definition(r), r["target_year"] - 1), [])
            if not p.get("selection_blocked")
            and p["available_date"][:10] <= r["available_date"][:10]
        ]
        comparisons = {}
        for mode in ("reported", "estimate", "actual"):
            choices = [
                p
                for p in candidates
                if (
                    p["status"] == "actual"
                    if mode == "actual"
                    else p["source"] == r["source"]
                    and (mode == "reported" or p["status"] == "estimate")
                )
            ]
            same_document = [p for p in choices if p["document_id"] == r["document_id"]]
            previous = latest(same_document or choices)
            reason = (
                "no_compatible_prior_year"
                if previous is None
                else "zero_prior_year" if previous["value"] == 0 else "available"
            )
            comparisons[mode] = dict(
                previous=(
                    {k: previous[k] for k in REFERENCE_FIELDS} if previous else None
                ),
                yoy=(
                    (r["value"] / previous["value"] - 1) * 100
                    if reason == "available"
                    else None
                ),
                reason=reason,
            )
        result.append({**r, "comparisons": comparisons})
    return result


def outlook_rows(
    production,
    target_year,
    status="forecast",
    source="auto",
    baseline="reported",
    subregion=None,
    crop=None,
):
    result = []
    crop = crop or (production[0].get("crop") if production else None) or "rice"
    for geo in geographies(crop):
        country = geo["country"]
        if subregion and geo["subregion"] != subregion:
            continue
        row = preferred(
            [
                r
                for r in production
                if r["country"] == country
                and not r["region"]
                and r["target_year"] == target_year
                and r["status"] == status
            ],
            country,
            source,
        )
        comparison = (
            row["comparisons"][baseline]
            if row
            else dict(previous=None, yoy=None, reason="no_observation_for_selection")
        )
        result.append(dict(**geo, production=row, **comparison))
    return result
