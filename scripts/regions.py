"""Fixed member baskets from one source document. Never sum different vintages."""

import hashlib
import json
from policy import POLICY, active_regions, region_members


def aggregate_regions(df, crop):
    result = []
    for name in active_regions(crop):
        cfg = POLICY["regions"][name]
        members = region_members(name, crop)
        all_source = df[
            df.source.eq(cfg["primary"])
            & df.region.eq("")
            & df.year_basis.eq(cfg["year_basis"])
        ]
        source = all_source[all_source.country.isin(members)]
        group_keys = [
            "document_id",
            "target_year",
            "year_basis",
            "commodity_basis",
            "metric",
            "unit",
            "status",
        ]
        for key, group in source.groupby(group_keys, sort=False):
            if group.iloc[0]["metric"] == "yield":
                continue
            group = group.drop_duplicates("country", keep="last")
            if set(group.country) != set(members):
                continue
            row = group.iloc[-1].to_dict()
            component = group.sort_values("country")[
                ["record_id", "country", "value"]
            ].to_dict("records")
            identity = json.dumps([POLICY["version"], name, *key], default=str)
            row.update(
                country=name,
                source_country=name,
                region="",
                value=float(group.value.sum()),
                record_id="region-" + hashlib.sha256(identity.encode()).hexdigest(),
                component_records=component,
                policy_version=POLICY["version"],
                member_count=len(members),
                methodology=f"{POLICY['version']}: fixed {name} basket; sum of {len(members)} members in one {cfg['primary']} document. Members: {', '.join(members)}. MY starting-year basket, not a common calendar harvest. Imports/exports are gross member trade including intra-region flows; not external-region trade.",
            )
            result.append(row)
        # Keep old vintages for review, but never silently select one when the
        # newest snapshot for that year is missing a configured member.
        selection_keys = [
            "target_year",
            "year_basis",
            "commodity_basis",
            "metric",
            "unit",
            "status",
        ]
        for key, group in all_source.groupby(selection_keys, sort=False):
            newest = group.sort_values(
                ["available_date", "download_timestamp", "document_id"]
            ).iloc[-1]
            snapshot = group[group.document_id.eq(newest.document_id)]
            missing = sorted(set(members) - set(snapshot.country))
            if missing:
                for row in result:
                    if row["country"] == name and all(
                        row[k] == v for k, v in zip(selection_keys, key)
                    ):
                        row["selection_blocked"] = True
                        row["missing_members"] = missing
        # Regional grain yield is production / area, never a mean of national yields.
        produced = [
            r
            for r in result
            if r["country"] == name
            and r["metric"] == "production"
            and r["commodity_basis"] not in ("milled", "paddy")
        ]
        for row in produced:
            area = next(
                (
                    a
                    for a in result
                    if a["country"] == name
                    and a["metric"] == "area"
                    and all(
                        a[k] == row[k]
                        for k in [
                            "document_id",
                            "target_year",
                            "commodity_basis",
                            "status",
                        ]
                    )
                ),
                None,
            )
            if area and area["value"] > 0:
                result.append(
                    {
                        **row,
                        "record_id": row["record_id"] + "-yield",
                        "metric": "yield",
                        "unit": "t/ha",
                        "value": row["value"] / area["value"],
                        "selection_blocked": bool(
                            row.get("selection_blocked")
                            or area.get("selection_blocked")
                        ),
                        "missing_members": sorted(
                            set(
                                row.get("missing_members", [])
                                + area.get("missing_members", [])
                            )
                        ),
                        "component_records": row["component_records"]
                        + area["component_records"],
                        "methodology": row["methodology"]
                        + " Regional yield = sum production / sum harvested area.",
                    }
                )
    return result
