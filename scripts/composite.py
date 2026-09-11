"""National production composites; missing national priors suppress YoY."""
from __future__ import annotations

from typing import Mapping, Any


def pair_components(
    psd: Mapping[int, Mapping[str, float]],
    local: Mapping[int, Mapping[str, float]],
    year: int,
    eligible: Mapping[str, bool] | None = None,
    source: str = "local",
) -> dict[str, Any]:
    if year not in psd or year - 1 not in psd:
        raise ValueError("PSD must contain target and prior year")
    eligible = eligible or {}
    current: dict[str, float] = {}
    previous: dict[str, float | None] = {}
    components: dict[str, dict[str, Any]] = {}
    for country in sorted(psd[year]):
        adopted = (
            eligible.get(country, True)
            and country in local.get(year, {})
        )
        current[country] = float(local[year][country] if adopted else psd[year][country])
        prior = local.get(year-1, {}).get(country) if adopted else psd[year-1].get(country)
        previous[country] = float(prior) if prior is not None else None
        components[country] = {
            "source": source if adopted else "usda_psd",
            "current": current[country],
            "previous": previous[country],
            "change": current[country] - previous[country] if previous[country] is not None else None,
            "replaced": adopted,
            "fallback_reason": None if adopted else "missing_eligible_local_target",
            "comparison_reason": "missing_local_prior" if adopted and prior is None else None,
        }
    cur = sum(current.values())
    prev = sum(previous.values()) if all(v is not None for v in previous.values()) else None
    return {
        "current": cur,
        "previous": prev,
        "change": cur - prev if prev is not None else None,
        "yoy": (cur / prev - 1) * 100 if prev else None,
        "components": components,
        "local_coverage_pct": (
            sum(v["current"] for country,v in components.items() if v["replaced"] or country == 'United States')
            / cur
            * 100
            if cur
            else 0.0
        ),
    }


def contribution_pp(change: float | None, composite_previous: float | None) -> float | None:
    """Contribution to global YoY in percentage points."""
    if change is None or not composite_previous:
        return None
    return change / composite_previous * 100
