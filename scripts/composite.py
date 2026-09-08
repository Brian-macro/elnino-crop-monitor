"""Paired-source production composites.

The key invariant is that a local source can replace a country only when both
the target year and the prior year are available under the same definition.
"""
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
    previous: dict[str, float] = {}
    components: dict[str, dict[str, Any]] = {}
    for country in sorted(psd[year]):
        has_pair = (
            eligible.get(country, True)
            and country in local.get(year, {})
            and country in local.get(year - 1, {})
        )
        current[country] = float(local[year][country] if has_pair else psd[year][country])
        previous[country] = float(local[year - 1][country] if has_pair else psd[year - 1][country])
        components[country] = {
            "source": source if has_pair else "usda_psd",
            "current": current[country],
            "previous": previous[country],
            "change": current[country] - previous[country],
            "replaced": has_pair,
            "fallback_reason": None if has_pair else "missing_local_pair",
        }
    cur, prev = sum(current.values()), sum(previous.values())
    return {
        "current": cur,
        "previous": prev,
        "change": cur - prev,
        "yoy": (cur / prev - 1) * 100 if prev else None,
        "components": components,
        "local_coverage_pct": (
            sum(v["previous"] for v in components.values() if v["replaced"])
            / sum(previous.values())
            * 100
            if prev
            else 0.0
        ),
    }


def contribution_pp(change: float | None, composite_previous: float | None) -> float | None:
    """Contribution to global YoY in percentage points."""
    if change is None or not composite_previous:
        return None
    return change / composite_previous * 100
