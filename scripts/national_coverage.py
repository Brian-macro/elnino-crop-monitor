"""Publish observed country/source coverage, independently of configured intent."""
import json
from pathlib import Path
from datetime import datetime, timezone
from policy import POLICY, COUNTRY_SOURCES, composite_rule


def national_coverage(con, dashboards):
    from config import SOURCES, ROOT
    authority_path = ROOT / 'config' / 'national_authorities.json'
    authorities = json.loads(authority_path.read_text(encoding='utf-8'))['countries'] if authority_path.exists() else []
    authority_map = {row['country']: row for row in authorities}
    rows = []
    for crop, dashboard in dashboards.items():
        for country in POLICY['active_countries'][crop]:
            rule = composite_rule(country, crop)
            country_rule = next((r for r in COUNTRY_SOURCES['rules'] if r['country']==country),None)
            source = rule['source'] if rule else 'usda_psd' if country == 'United States' else country_rule['source'] if country_rule else None
            available = con.execute('''SELECT target_year,year_basis,commodity_basis,status,value,source_url
                FROM production_all WHERE crop=? AND country=? AND source=? AND region=''
                AND metric='production' AND available_date<=current_date
                QUALIFY row_number() OVER(PARTITION BY target_year,year_basis,commodity_basis
                    ORDER BY available_date DESC,download_timestamp DESC,record_id DESC)=1
                ORDER BY target_year DESC''', [crop,country,source]).fetchall() if source else []
            compatible = [r for r in available if not rule or (r[1] == rule['year_basis'] and r[2] == rule['commodity_basis'])]
            latest = compatible[0] if compatible else available[0] if available else None
            years = {}
            for year, snapshot in dashboard['years'].items():
                evidence = snapshot['source_evidence'].get(country, {})
                selected = evidence.get('source', 'usda_psd')
                local = selected != 'usda_psd' or country == 'United States'
                years[year] = dict(source=selected, adopted_national=local,
                    source_url=evidence.get('source_url') or snapshot['baseline'].get('source_url'),
                    reason=evidence.get('fallback_reason') or (None if local else 'national_source_not_integrated'),
                    comparison_reason=evidence.get('comparison_reason'),
                    source_target_year=evidence.get('source_target_year', int(year)))
            registry = SOURCES.get(source,{})
            authority = authority_map.get(country,{})
            rows.append(dict(country=country,crop=crop,configured_source=source,
                authority=authority.get('authority') or registry.get('name'),
                authority_url=authority.get('url') or registry.get('url'),
                access_status=authority.get('access_status'), note=authority.get('note') or (rule or {}).get('note'),
                access_error=authority.get('access_error'),
                eligible=rule.get('eligible',False) if rule else country == 'United States',
                available_years=sorted({int(r[0]) for r in compatible}),
                latest_national=dict(target_year=int(latest[0]),year_basis=latest[1],commodity_basis=latest[2],
                    status=latest[3],value=float(latest[4]),source_url=latest[5]) if latest else None,
                years=years))
    return dict(generated_at=datetime.now(timezone.utc).isoformat(),policy_version=POLICY['version'],
        source_policy_version=COUNTRY_SOURCES['version'],rows=rows)
