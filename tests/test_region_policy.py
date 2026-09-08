import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def rows_for(crop="corn"):
    from policy import POLICY

    members = POLICY["regions"]["Southeast Asia"]["members_by_crop"][crop]
    return pd.DataFrame(
        [
            dict(
                record_id=f"{country}-{year}",
                document_id="snapshot",
                country=country,
                source_country=country,
                crop=crop,
                region="",
                target_year=year,
                year_basis="marketing_year",
                commodity_basis="milled" if crop == "rice" else "grain",
                metric="production",
                unit="Mt",
                value=float(i + 1) * (2 if year == 2026 else 1),
                source="usda_psd",
                status="forecast",
                publication_date=None,
                available_date=pd.Timestamp("2026-08-12"),
                download_timestamp=pd.Timestamp("2026-08-12"),
                source_url="https://example.org/psd",
                methodology="fixture",
            )
            for year in [2025, 2026]
            for i, country in enumerate(members)
        ]
    )


def test_materiality_is_crop_specific_and_fixed():
    from policy import active_countries, region_members

    assert "Malaysia" in active_countries("rice")
    assert "Malaysia" not in active_countries("sugar")
    assert region_members("Southeast Asia", "wheat") == []
    assert set(region_members("Southeast Asia", "sugar")) == {
        "Thailand",
        "Vietnam",
        "Indonesia",
        "Philippines",
        "Burma",
    }
    for crop in ["wheat", "corn", "rice", "soybean", "sugar"]:
        assert not {"Hong Kong", "Macau", "Singapore"} & set(active_countries(crop))


def test_region_sum_and_yoy_use_same_fixed_members():
    from regions import aggregate_regions
    from research import records
    from outlook import enrich_comparisons

    source = rows_for()
    derived = aggregate_regions(source, "corn")
    assert len(derived) == 2
    by_year = {r["target_year"]: r for r in derived}
    assert by_year[2026]["value"] == 56
    assert by_year[2025]["value"] == 28
    assert len(by_year[2026]["component_records"]) == 7
    result = enrich_comparisons(records(pd.DataFrame(derived)))
    assert (
        next(r for r in result if r["target_year"] == 2026)["comparisons"]["reported"][
            "yoy"
        ]
        == 100
    )


def test_region_missing_member_and_mixed_vintage_do_not_publish_partial_total():
    from regions import aggregate_regions

    source = rows_for()
    missing = source[~((source.country == "Thailand") & (source.target_year == 2026))]
    assert {r["target_year"] for r in aggregate_regions(missing, "corn")} == {2025}
    mixed = source.copy()
    mixed.loc[
        (mixed.country == "Thailand") & (mixed.target_year == 2026), "document_id"
    ] = "another_snapshot"
    assert {r["target_year"] for r in aggregate_regions(mixed, "corn")} == {2025}


def test_primary_source_never_silently_falls_back():
    from policy import annotate_rows
    from outlook import preferred

    sample = rows_for().iloc[0].to_dict()
    annotated = annotate_rows(pd.DataFrame([{**sample, "source": "usda_wasde"}]))
    assert preferred(annotated.to_dict("records"), "Thailand") is None
    assert (
        preferred(annotated.to_dict("records"), "Thailand", "usda_wasde")["source"]
        == "usda_wasde"
    )


def test_china_short_long_term_and_actual_policy():
    from policy import primary_source

    assert primary_source("China", "forecast", 2026, "2026-08-31") == "cropwatch"
    assert primary_source("China", "forecast", 2035, "2026-04-20") == "china_outlook"
    assert primary_source("China", "actual", 2025, "2025-12-12") == "nbs"
    assert (
        primary_source("Southeast Asia", "forecast", 2026, "2026-08-12") == "usda_psd"
    )


def test_schedule_due_check_is_source_specific():
    from scheduler import select_jobs

    jobs = [
        dict(
            id="weekly",
            group="crops",
            script="x.py",
            args=[],
            sources=["x"],
            interval_days=7,
        )
    ]
    assert select_jobs(jobs, {"x": "2026-09-07"}, "2026-09-08", due=True) == []
    assert len(select_jobs(jobs, {"x": "2026-09-01"}, "2026-09-08", due=True)) == 1
    assert len(select_jobs(jobs, {"x": "2026-09-07"}, "2026-09-08", due=False)) == 1


def test_new_incomplete_snapshot_does_not_silently_select_old_regional_total():
    from regions import aggregate_regions
    from outlook import preferred

    source = rows_for()
    later = source[source.country != "Thailand"].copy()
    later["document_id"] = "later"
    later["available_date"] = pd.Timestamp("2026-09-01")
    result = aggregate_regions(pd.concat([source, later]), "corn")
    latest = [r for r in result if r["target_year"] == 2026]
    assert len(latest) == 1 and latest[0]["value"] == 56
    assert latest[0]["selection_blocked"] and latest[0]["missing_members"] == [
        "Thailand"
    ]
    assert preferred(latest, "Southeast Asia") is None


def test_whole_missing_basket_is_detected_from_other_countries_in_new_document():
    from regions import aggregate_regions

    source = rows_for()
    later = source.iloc[[0]].copy()
    later["country"] = "United States"
    later["document_id"] = "later"
    later["available_date"] = pd.Timestamp("2026-09-01")
    later["target_year"] = 2026
    result = aggregate_regions(pd.concat([source, later]), "corn")
    assert next(r for r in result if r["target_year"] == 2026)["selection_blocked"]


def test_blocked_prior_year_is_not_yoy_baseline_or_history():
    from regions import aggregate_regions
    from research import records, history_rows
    from outlook import enrich_comparisons

    old = rows_for()
    old.loc[old.target_year.eq(2025), "status"] = "estimate"
    later = old[~(old.country.eq("Thailand") & old.target_year.eq(2025))].copy()
    later["document_id"] = "later"
    later["available_date"] = pd.Timestamp("2026-09-01")
    derived = aggregate_regions(pd.concat([old, later]), "corn")
    data = records(pd.DataFrame(derived).fillna({"selection_blocked": False}))
    selected = next(
        r
        for r in enrich_comparisons(data)
        if r["target_year"] == 2026 and r["document_id"] == "later"
    )
    assert selected["comparisons"]["reported"]["previous"] is None
    assert history_rows(pd.DataFrame(derived)) == []


def test_regional_yield_inherits_incomplete_area_state():
    from regions import aggregate_regions

    production = rows_for()
    area = production.copy()
    area["metric"] = "area"
    area["unit"] = "Mha"
    area["value"] = area["value"] / 2
    old = pd.concat([production, area])
    later = old[~(old.country.eq("Thailand") & old.metric.eq("area"))].copy()
    later["document_id"] = "later"
    later["available_date"] = pd.Timestamp("2026-09-01")
    result = aggregate_regions(pd.concat([old, later]), "corn")
    yields = [r for r in result if r["metric"] == "yield"]
    assert yields and all(r["selection_blocked"] for r in yields)
