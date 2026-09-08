"""Small, comparable dashboard payload. Top five and residual share one PSD vintage."""
from datetime import date,datetime,timezone
from policy import POLICY,active_countries,active_regions,region_members
from normalize import EU_MEMBERS
from geography import canonical_country,geography_metadata

def summarize_counts(current,previous,units):
    def entry(name,members):
        value=sum(current[c] for c in members)
        prior=sum(previous[c] for c in members) if all(c in previous for c in members) else None
        return dict(name=name,value=value,previous=prior,yoy=(value/prior-1)*100 if prior else None,
            change=value-prior if prior is not None else None,members=sorted(members))
    world=entry('Global',list(current))
    candidates=[entry(name,members) for name,members in units.items() if members and all(c in current for c in members)]
    candidates=[r for r in candidates if r['value']>0]
    top=sorted(candidates,key=lambda r:(-r['value'],r['name']))[:5]
    covered=[c for row in top for c in row['members']]
    if len(covered)!=len(set(covered)):raise ValueError('Overlapping top-five research units')
    remaining=sorted(set(current)-set(covered))
    others=entry('其他',remaining)
    others['members']=[c for c in remaining if current[c]>0 or previous.get(c,0)>0]
    ranking=top+[others]
    for row in ranking:row['share']=row['value']/world['value']*100 if world['value'] else None
    if abs(sum(r['value'] for r in ranking)-world['value'])>1e-6:raise ValueError('Dashboard residual does not reconcile')
    return dict(world=world,ranking=ranking,top5_share=sum(r['share'] or 0 for r in top))

def dashboard_bundle(con,crop):
    raw=con.execute('''SELECT p.*,d.publication_date_basis FROM production_all p JOIN source_documents d USING(document_id)
      WHERE p.crop=? AND p.source='usda_psd' AND p.metric='production' AND p.region='' AND p.available_date<=current_date
      ORDER BY p.available_date,p.download_timestamp,p.document_id''',[crop]).fetchdf()
    if raw.empty:return dict(crop=crop,years={},history=[],geographies=[],updated=None,policy_version=POLICY['version'],methodology='暂无可用的USDA PSD可比数据')
    # Each year's figure and previous-year baseline come from the SAME full snapshot.
    years={};history=[]
    for year,group in raw.groupby('target_year',sort=True):
        latest=group.iloc[-1];doc=latest.document_id
        selected=raw[raw.document_id.eq(doc)]
        current=selected[selected.target_year.eq(year)].copy();previous=selected[selected.target_year.eq(year-1)].copy()
        for frame in (current,previous):
            if 'European Union' in set(frame.country):frame.drop(frame[frame.country.isin(EU_MEMBERS)].index,inplace=True)
        current_counts={canonical_country(r.country):float(r.value) for r in current.itertuples()}
        previous_counts={canonical_country(r.country):float(r.value) for r in previous.itertuples()}
        units={country:[country] for country in current_counts if country not in POLICY['excluded_entities']}
        for name in active_regions(crop):
            members=region_members(name,crop)
            for country in members:units.pop(country,None)
            units[name]=members
        summary=summarize_counts(current_counts,previous_counts,units)
        # Until a validated local pair exists, expose an explicit PSD baseline
        # contract. The frontend can render the comparison fields without
        # mistaking a missing local source for a zero-difference result.
        summary['mode'] = 'psd_baseline'
        summary['local_coverage_pct'] = 0.0
        summary['baseline'] = dict(
            source='usda_psd',
            value=summary['world']['value'],
            previous=summary['world']['previous'],
            yoy=summary['world']['yoy'],
        )
        summary['world']['baseline_yoy'] = summary['world']['yoy']
        summary['world']['yoy_spread_pp'] = 0.0
        for row in summary['ranking']:
            row['contribution_pp'] = (
                row['change'] / summary['world']['previous'] * 100
                if row.get('change') is not None and summary['world']['previous']
                else None
            )
        # Compact regional details remain available on click; the default shows only six rows.
        summary.update(target_year=int(year),status=latest.status,source='usda_psd',source_url=latest.source_url,
            available_date=str(latest.available_date)[:10],publication_date=str(latest.publication_date)[:10] if str(latest.publication_date)!='NaT' else None,
            download_timestamp=str(latest.download_timestamp),document_id=doc,commodity_basis=latest.commodity_basis,year_basis=latest.year_basis)
        summary['world'].pop('members',None)
        years[str(year)]=summary
        history.append(dict(year=int(year),value=summary['world']['value'],yoy=summary['world']['yoy'],status=latest.status))
    countries=sorted({canonical_country(c) for c in raw.country})
    return dict(crop=crop,years=years,history=history,geographies=[geography_metadata(c) for c in countries],
        updated=datetime.now(timezone.utc).isoformat(),policy_version=POLICY['version'],
        methodology='全球地图与前五排行统一为USDA PSD可比口径；其他=同一快照全球余下成员的总和。中国独立研究来源在详情中保留。历史Estimate与Forecast分开，不补缺失值。')
