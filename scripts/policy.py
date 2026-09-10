"""One research policy: materiality, primary sources, fixed regions and schedules."""

import json
from pathlib import Path
from geography import geography_metadata

POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "research_policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
COUNTRY_SOURCE_PATH = POLICY_PATH.with_name("country_sources.json")
COUNTRY_SOURCES = json.loads(COUNTRY_SOURCE_PATH.read_text(encoding="utf-8"))


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


def composite_rule(country, crop):
    return next((r for r in COUNTRY_SOURCES["rules"] if r["country"] == country and r["crop"] == crop), None)


def local_source(country, crop):
    rule = composite_rule(country, crop)
    return rule["source"] if rule and rule.get("eligible") else None


def active_countries(crop):
    return POLICY["active_countries"][crop]


def region_members(region, crop):
    return POLICY["regions"].get(region, {}).get("members_by_crop", {}).get(crop, [])


def active_regions(crop):
    return [name for name in POLICY["regions"] if region_members(name, crop)]


def primary_source(country, status, target_year, available_date, crop=None):
    if crop and status == "forecast":
        if country == "China" and target_year > int(str(available_date)[:4]) + POLICY["source_priority"]["china"]["horizon_boundary"]:
            return "china_outlook"
        return local_source(country, crop) or "usda_psd"
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
        r.source == primary_source(r.country, r.status, r.target_year, r.available_date, getattr(r, "crop", None))
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
            rule = composite_rule(unit, crop)
            aggregate = unit == 'Global' or unit in POLICY['regions']
            matrix.append(
                dict(
                    crop=crop,
                    unit=unit,
                    members=region_members(unit, crop),
                    history="usda_psd",
                    actual="faostat" if unit == "Global" else "nbs" if china else None,
                    forecast='local_composite' if aggregate else local_source(unit, crop) or 'usda_psd',
                    configured_local_source=rule['source'] if rule else None,
                    fallback='usda_psd',
                    fallback_reason=(None if aggregate or (rule and rule.get('eligible')) else
                                     rule.get('reason', 'definition_unverified') if rule else 'no_local_source'),
                    long_term="china_outlook" if china else None,
                    reference=(
                        []
                        if unit in POLICY["regions"]
                        else ["usda_wasde", "cropwatch"] if not china else ["usda_psd"]
                    ),
                    splice=(
                        "有本国预测数据用本国预测数据，无则用PSD；同比只在本年和上年口径可比时计算。"
                    ),
                    mean=False,
                )
            )
    return {
        **POLICY,
        'country_sources': COUNTRY_SOURCES,
        "source_matrix": matrix,
        "research_units": {
            crop: research_units(crop) for crop in POLICY["active_countries"]
        },
    }
