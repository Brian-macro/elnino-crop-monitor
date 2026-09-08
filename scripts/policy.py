"""One research policy: materiality, primary sources, fixed regions and schedules."""

import json
from pathlib import Path
from geography import geography_metadata

POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "research_policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def validate_policy(policy=POLICY):
    if not policy.get("version"):
        raise ValueError("Policy version required")
    excluded = set(policy["excluded_entities"])
    for crop, countries in policy["active_countries"].items():
        if len(countries) != len(set(countries)) or excluded.intersection(countries):
            raise ValueError("Invalid crop universe: " + crop)
    for name, region in policy["regions"].items():
        for crop, members in region["members_by_crop"].items():
            if len(members) != len(set(members)) or not set(members) <= set(
                policy["active_countries"][crop]
            ):
                raise ValueError("Invalid region members: " + name + "/" + crop)
        if region["aggregation"] != "sum_complete_same_document":
            raise ValueError("Unsupported aggregation")
    return True


validate_policy()


def active_countries(crop):
    return POLICY["active_countries"][crop]


def region_members(region, crop):
    return POLICY["regions"].get(region, {}).get("members_by_crop", {}).get(crop, [])


def active_regions(crop):
    return [name for name in POLICY["regions"] if region_members(name, crop)]


def primary_source(country, status, target_year, available_date):
    if country in POLICY["regions"]:
        return POLICY["regions"][country]["primary"]
    if country != "China":
        return POLICY["source_priority"]["overseas"]["primary"]
    china = POLICY["source_priority"]["china"]
    if status == "actual":
        return china["actual"]
    issued_year = int(str(available_date)[:4])
    return (
        china["long_term"]
        if target_year > issued_year + china["horizon_boundary"]
        else china["near_term"]
    )


def annotate_rows(df):
    df = df.copy()
    df["is_primary"] = [
        r.source == primary_source(r.country, r.status, r.target_year, r.available_date)
        for r in df.itertuples()
    ]
    return df


def geographies(crop):
    result = []
    for country in ["Global"] + active_countries(crop):
        parent = next(
            (
                name
                for name in active_regions(crop)
                if country in region_members(name, crop)
            ),
            None,
        )
        result.append(
            {
                **geography_metadata(country),
                "level": "country" if country != "Global" else "global",
                "parent": parent,
            }
        )
    for name in active_regions(crop):
        result.append(
            dict(
                country=name,
                map_name=None,
                label=POLICY["regions"][name]["label"],
                subregion=name,
                level="region",
                parent="Global",
                members=region_members(name, crop),
            )
        )
    return result


def research_units(crop):
    return [
        g["country"]
        for g in geographies(crop)
        if g["level"] in ("global", "region") or g["parent"] is None
    ]


def policy_bundle():
    matrix = []
    for crop in POLICY["active_countries"]:
        for unit in research_units(crop):
            china = unit == "China"
            matrix.append(
                dict(
                    crop=crop,
                    unit=unit,
                    members=region_members(unit, crop),
                    history="usda_psd (MY reference)" if china else "usda_psd",
                    actual="nbs" if china else None,
                    forecast="cropwatch" if china else "usda_psd",
                    long_term="china_outlook" if china else None,
                    reference=(
                        []
                        if unit in POLICY["regions"]
                        else ["usda_wasde", "cropwatch"] if not china else ["usda_psd"]
                    ),
                    splice=(
                        "separate CY/MY segments"
                        if china
                        else "same-source / same-definition"
                    ),
                    mean=False,
                )
            )
    return {
        **POLICY,
        "source_matrix": matrix,
        "research_units": {
            crop: research_units(crop) for crop in POLICY["active_countries"]
        },
    }
