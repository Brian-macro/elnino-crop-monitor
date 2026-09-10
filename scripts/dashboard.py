"""Local paired production on a PSD baseline, with explicit component provenance."""
from datetime import date,datetime,timezone
from policy import POLICY,COUNTRY_SOURCES,active_countries,active_regions,region_members
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

def apply_local_pairs(con,crop,year,current,previous,asof=None):
    """Replace both years together; never calculate YoY across two sources."""
    evidence={};asof=asof or date.today().isoformat()
    for rule in COUNTRY_SOURCES['rules']:
        if rule['crop']!=crop:continue
        country,source=rule['country'],rule['source']
        if not rule.get('eligible'):
            evidence[country]=dict(source='usda_psd',configured_source=source,fallback_reason=rule.get('reason','definition_unverified'))
            continue
        offset=int(rule.get('source_target_year_offset',0));source_year=year+offset
        rows=con.execute('''SELECT target_year,value,record_id,available_date,source_url,publication_date,status,document_id,year_basis,download_timestamp FROM production_all
          WHERE crop=? AND country=? AND region='' AND source=? AND metric='production'
            AND commodity_basis=? AND year_basis=? AND target_year IN (?,?) AND available_date<=?
          QUALIFY row_number() OVER(PARTITION BY target_year ORDER BY available_date DESC,download_timestamp DESC,record_id DESC)=1''',
          [crop,country,source,rule['commodity_basis'],rule['year_basis'],source_year-1,source_year,asof]).fetchall()
        by_year={int(r[0]):r for r in rows}
        if source_year in by_year and source_year-1 in by_year and country in current and country in previous:
            current[country]=float(by_year[source_year][1]);previous[country]=float(by_year[source_year-1][1])
            row=by_year[source_year]; prior=by_year[source_year-1]
            evidence[country]=dict(source=source,current_record=row[2],previous_record=prior[2],source_target_year=source_year,fallback_reason=None,
                source_url=row[4],available_date=str(max(row[3],prior[3]))[:10],publication_date=str(row[5])[:10] if row[5] else None,
                status=row[6],document_id=row[7],year_basis=row[8],download_timestamp=str(max(row[9],prior[9])))
        else:evidence[country]=dict(source='usda_psd',configured_source=source,fallback_reason='missing_local_pair')
    return evidence

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
        baseline_current=sum(current_counts.values());baseline_previous=sum(previous_counts.values()) if previous_counts else None
        evidence=apply_local_pairs(con,crop,int(year),current_counts,previous_counts)
        units={country:[country] for country in current_counts if country not in POLICY['excluded_entities']}
        for name in active_regions(crop):
            members=region_members(name,crop)
            for country in members:units.pop(country,None)
            units[name]=members
        summary=summarize_counts(current_counts,previous_counts,units)
        # Until a validated local pair exists, expose an explicit PSD baseline
        # contract. The frontend can render the comparison fields without
        # mistaking a missing local source for a zero-difference result.
        replaced={c for c,e in evidence.items() if e.get('source')!='usda_psd'}
        summary['mode'] = 'local_composite' if replaced else 'psd_baseline'
        summary['local_coverage_pct'] = (sum(previous_counts[c] for c in replaced)/summary['world']['previous']*100 if replaced and summary['world']['previous'] else 0.0)
        summary['baseline'] = dict(
            source='usda_psd',
            value=baseline_current,
            previous=baseline_previous,
            yoy=(baseline_current/baseline_previous-1)*100 if baseline_previous else None,
        )
        summary['world']['forecast_gap'] = summary['world']['value'] - baseline_current
        summary['world']['baseline_yoy'] = summary['baseline']['yoy']
        summary['world']['yoy_spread_pp'] = summary['world']['yoy']-summary['baseline']['yoy'] if summary['world']['yoy'] is not None and summary['baseline']['yoy'] is not None else None
        summary['source_evidence']=evidence
        china_evidence=evidence.get('China',dict(source='usda_psd',fallback_reason='no_local_source'))
        china_current=current_counts.get('China');china_previous=previous_counts.get('China')
        summary['china']=dict(value=china_current,previous=china_previous,
            yoy=(china_current/china_previous-1)*100 if china_current is not None and china_previous else None,
            source_url=latest.source_url,available_date=str(latest.available_date)[:10],status=latest.status,
            year_basis=latest.year_basis,document_id=doc)
        summary['china'].update(china_evidence)
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
        summary['baseline']['source_url']=latest.source_url
        summary['baseline']['available_date']=str(latest.available_date)[:10]
        if replaced:
            summary.update(source='local_composite',source_url=None,publication_date=None,document_id=None,
                available_date=max([str(latest.available_date)[:10]]+[evidence[c]['available_date'] for c in replaced]),
                download_timestamp=max([str(latest.download_timestamp)]+[evidence[c]['download_timestamp'] for c in replaced]))
        summary['world'].pop('members',None)
        years[str(year)]=summary
        history.append(dict(year=int(year),value=summary['world']['value'],yoy=summary['world']['yoy'],status=latest.status))
    countries=sorted({canonical_country(c) for c in raw.country})
    return dict(crop=crop,years=years,history=history,geographies=[geography_metadata(c) for c in countries],
        updated=datetime.now(timezone.utc).isoformat(),policy_version=POLICY['version'],
        methodology='有本国预测数据用本国预测数据，无则用PSD；同比仅在本年和上年同源、同产品且年度可对应时计算。全球、地图和前五加其他使用同一组合；覆盖率按组合上年产量计算。历史为当前归档的修订值，不代表事件当时的预测。')
