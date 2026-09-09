"""Retrospective ENSO windows: futures and spot series remain separate."""

from datetime import datetime, timezone,date
from collections import defaultdict
import math
import pandas as pd
from analytics import monthly_prices, month_index, month_label
from futures_config import CONTRACTS
from config import BASIS
from normalize import EU_MEMBERS
from research import records, climate_bundle
from policy import POLICY

def monthly_futures(rows,domestic,today=None):
    cutoff=str(today or date.today())[:7]
    cfg=POLICY['quality']['futures_monthly'];groups=defaultdict(list)
    for row in rows:groups[str(row['date'])[:7]].append(row)
    values={};quality={}
    for month,observations in sorted(groups.items()):
        valid=[]
        for row in observations:
            prices=[row.get(k) for k in ['open','high','low','close']]
            if any(v is None or not math.isfinite(float(v)) for v in prices):continue
            if row['low']<=row['open']<=row['high'] and row['low']<=row['close']<=row['high'] and row['low']>0:valid.append(row)
        # Duplicate observations must not make sparse months look well covered.
        valid=list({str(row['date'])[:10]:row for row in valid}.values())
        volume=sum(row.get('volume') or 0 for row in valid)
        reason='incomplete_month' if month>=cutoff else 'thin_sample' if len(valid)<cfg['min_observed_days'] else 'thin_volume' if domestic and volume<cfg['min_domestic_volume'] else 'usable'
        quality[month]=dict(n_obs=len(valid),raw_obs=len(observations),invalid_ohlc=len(observations)-len(valid),
            first_date=min((str(r['date'])[:10] for r in valid),default=None),last_date=max((str(r['date'])[:10] for r in valid),default=None),
            volume=volume if domestic or volume else None,expected_sessions=None,reason=reason)
        if reason=='usable':values[month]=sum(r['close'] for r in valid)/len(valid)
    return values,quality


def stocks_to_use(stocks, consumption):
    return (
        stocks / consumption * 100
        if stocks is not None and consumption is not None and consumption > 0
        else None
    )


def price_window(domestic, overseas, months):
    d = [domestic.get(m) for m in months]
    o = [overseas.get(m) for m in months]
    common = next((m for m in months if domestic.get(m) and overseas.get(m)), None)
    both = any(v is not None for v in d) and any(v is not None for v in o)
    base = (
        common
        if both
        else next((m for m in months if domestic.get(m) or overseas.get(m)), None)
    )

    def indexed(values, monthly):
        denominator = monthly.get(base) if base else None
        return [
            v / denominator * 100 if v is not None and denominator else None
            for v in values
        ]

    def change(values):
        return (
            (values[-1] / values[0] - 1) * 100
            if values and values[0] and values[-1] is not None
            else None
        )

    return dict(
        base_month=base,
        domestic_values=d,
        overseas_values=o,
        domestic_index=indexed(d, domestic),
        overseas_index=indexed(o, overseas),
        domestic_change=change(d),
        overseas_change=change(o),
        domestic_months=sum(v is not None for v in d),
        overseas_months=sum(v is not None for v in o),
    )


def balance_rows(con, crop):
    df = con.execute(
        """SELECT p.*,d.title FROM production_all p JOIN source_documents d USING(document_id)
      WHERE crop=? AND p.source IN ('usda_psd','usda_wasde') AND p.region='' AND p.metric IN ('production','ending_stocks','consumption')
        AND p.commodity_basis=? AND p.available_date<=current_date
      ORDER BY p.available_date,p.download_timestamp,p.document_id""",
        [crop, BASIS[crop]],
    ).fetchdf()
    result = {"usda_psd": {}, "usda_wasde": {}}
    for (source, year), g in df.groupby(["source", "target_year"], sort=True):
        last = g.iloc[-1]
        g = g[g.document_id.eq(last.document_id)].drop_duplicates(
            ["country", "metric"], keep="last"
        )
        annual = {}
        for country in ["Global", "China"]:
            scoped = g[g.country.eq(country)].copy()
            derived = False
            if country == "Global" and source == "usda_psd":
                scoped = g[~g.country.eq("Global")].copy()
                derived = True
                if "European Union" in set(scoped.country):
                    scoped = scoped[~scoped.country.isin(EU_MEMBERS)]
            metrics = {}
            production_countries = set(scoped[scoped.metric.eq("production")].country)
            for metric in ["production", "ending_stocks", "consumption"]:
                values = scoped[scoped.metric.eq(metric)]
                complete = not values.empty and (
                    not derived or set(values.country) == production_countries
                )
                metrics[metric] = float(values.value.sum()) if complete else None
            annual[country] = dict(
                **metrics,
                stocks_to_use=stocks_to_use(
                    metrics["ending_stocks"], metrics["consumption"]
                ),
                source=source,
                source_url=last.source_url,
                document_id=last.document_id,
                available_date=str(last.available_date)[:10],
                publication_date=(
                    None
                    if pd.isna(last.publication_date)
                    else str(last.publication_date)[:10]
                ),
                target_year=int(year),
                year_basis=last.year_basis,
                commodity_basis=last.commodity_basis,
                status=last.status,
                derived_global=derived,
                unit="Mt",
                consumption_definition=('WASDE world use adjusted for differences between world imports and exports'
                    if source=='usda_wasde' and country=='Global' and crop in ('wheat','corn','rice') else
                    'Total Disappearance (human consumption + other domestic disappearance)' if crop=='sugar' else
                    'Sum of national Domestic Consumption' if derived else 'Domestic Consumption'),
                ratio_scope='Ending stocks / displayed consumption or use; not identical denominator across PSD and WASDE world series'
            )
        result[source][str(year)] = annual
    return result


def local_production_rows(dashboard):
    """Share the exact dashboard production; never synthesize a mixed-source balance."""
    result = {}
    for year, snap in dashboard['years'].items():
        common = dict(ending_stocks=None, consumption=None, stocks_to_use=None,
            target_year=int(year), commodity_basis=snap['commodity_basis'], unit='Mt',
            publication_date=None, derived_global=False)
        result[year] = {
            'Global': dict(**common, production=snap['world']['value'], yoy=snap['world']['yoy'],
                source=snap['source'], source_url=snap['source_url'], document_id=snap['document_id'],
                available_date=snap['available_date'], year_basis=snap['year_basis'], status=snap['status'],
                local_coverage_pct=snap['local_coverage_pct'], source_evidence=snap['source_evidence'],
                baseline_source_url=snap['baseline'].get('source_url'),
                fallback_reason='no_comparable_local_pairs' if snap['mode']=='psd_baseline' else None),
            'China': dict(**common, production=snap['china']['value'], **{k:v for k,v in snap['china'].items()
                if k in ('source','source_url','document_id','available_date','year_basis','status','fallback_reason','yoy','source_target_year')}),
        }
    return result


def event_bundle(con, crop, climate=None, dashboard=None):
    climate = climate or climate_bundle(con)
    if dashboard is None:
        from dashboard import dashboard_bundle
        dashboard = dashboard_bundle(con, crop)
    future = records(
        con.execute(
            """SELECT * FROM (SELECT f.*,d.source_url,d.download_timestamp FROM futures_prices f
       JOIN source_documents d USING(document_id) WHERE f.crop=? AND f.date<current_date
       QUALIFY row_number() OVER(PARTITION BY f.series_id,f.date ORDER BY f.available_date DESC,d.download_timestamp DESC)=1
       ) latest WHERE usable ORDER BY date""",
            [crop],
        ).fetchdf()
    )
    series = {}
    metadata = {}
    quality={}
    for ident, cfg in CONTRACTS.items():
        if cfg["crop"] != crop:
            continue
        rows = [r for r in future if r["series_id"] == ident]
        series[ident],quality[ident]=monthly_futures(rows,domestic=cfg['market']=='china')
        metadata[ident] = {
            **cfg,
            "series_id": ident,
            "first_date": rows[0]["date"][:10] if rows else None,
            "last_date": rows[-1]["date"][:10] if rows else None,
            "observations": len(rows),
            "download_timestamp": max(
                (r["download_timestamp"] for r in rows), default=None
            ),
            'monthly_quality':quality[ident],
            'usable_months':len(series[ident]),
            'last_usable_month':max(series[ident],default=None),
        }
    spot = records(
        con.execute(
            """SELECT p.*,d.source_url,d.download_timestamp FROM prices p JOIN source_documents d USING(document_id)
        WHERE p.crop=? AND p.source='worldbank' QUALIFY row_number() OVER(PARTITION BY p.symbol,p.date ORDER BY p.available_date DESC,d.download_timestamp DESC)=1 ORDER BY p.date""",
            [crop],
        ).fetchdf()
    )
    series["worldbank"] = monthly_prices(spot)
    metadata["worldbank"] = dict(
        series_id="worldbank",
        label="海外现货参考 · World Bank",
        symbol=spot[-1]["symbol"] if spot else None,
        source="worldbank",
        source_url=spot[-1]["source_url"] if spot else None,
        unit=spot[-1]["unit"] if spot else None,
        first_date=spot[0]["date"][:10] if spot else None,
        last_date=spot[-1]["date"][:10] if spot else None,
        observations=len(spot),
        download_timestamp=spot[-1]["download_timestamp"] if spot else None,
    )
    domestic = [
        ident
        for ident, cfg in CONTRACTS.items()
        if cfg["crop"] == crop and cfg["market"] == "china"
    ]
    overseas = next(
        (
            ident
            for ident, cfg in CONTRACTS.items()
            if cfg["crop"] == crop and cfg["market"] == "overseas"
        ),
        None,
    )
    oni = {p["date"][:7]: p["value"] for p in climate.get("series", {}).get("ONI", [])}
    windows = {}
    for event in climate["events"]:
        anchor = month_index(event["start"])
        months = [month_label(i) for i in range(anchor - 12, anchor + 13)]
        options = {}
        for ident in domestic:
            for mode, foreign in [("futures", overseas), ("spot", "worldbank")]:
                values = price_window(
                    series.get(ident, {}), series.get(foreign, {}), months
                )
                options[ident + "|" + mode] = {
                    **values,
                    "domestic_series": ident,
                    "overseas_series": foreign,
                    'domestic_quality':[quality.get(ident,{}).get(m,{'n_obs':0,'reason':'no_observations'}) for m in months],
                    'overseas_quality':[quality.get(foreign,{}).get(m,{'n_obs':1 if m in series.get(foreign,{}) else 0,'reason':'published_monthly' if m in series.get(foreign,{}) else 'no_observations'}) for m in months],
                }
        windows[event["id"]] = dict(
            months=months,
            oni=[oni.get(m) for m in months],
            years=sorted({int(m[:4]) for m in months}),
            options=options,
        )
    return dict(
        crop=crop,
        generated_at=datetime.now(timezone.utc).isoformat(),
        events=climate["events"],
        windows=windows,
        annual={**balance_rows(con, crop), 'local_composite': local_production_rows(dashboard)},
        default_production_source='local_composite',
        series=metadata,
        domestic_options=domestic,
        default_domestic=domestic[0] if domestic else None,
        notes=[
            "价格为供应商主连/连续序列月均报价，不是可投资收益；未完成月份、OHLC不一致报价和国内无成交报价不用于月均。",
            '月均至少需要10个有效观测日，国内月累计成交至少100手；这是最低样本筛选，不证明完整交易日覆盖或足够交易流动性。',
            "指数基期为窗口内首个共同观测月；只有一条价格序列时用该序列首个观测月。",
            "原币种与交割品级不同，指数用于走势复盘，不代表人民币价差或套利空间。",
            "主连换月可能造成跳变；供应商未提供每期实际交割合约，不假造换月明细。",
            "年度数据为当前归档的修订后历史值或预测，不代表事件当时已知数据；MY按来源年度编号对应，实际开始月份未经逐国逐作物校验。",
            '产量主线与首页共用本土同源成对组合；早期没有本土可比数据时明确回退PSD历史估计。当前预测不会被当作早期事件当时已知的预测。',
            '本土组合仅用于产量。库存、消费与库存消费比只在独立的PSD/WASDE供需参考中显示，不跨机构拼造供需平衡表。',
            'T是事后识别的首个暖季中心月，不是当时确认或交易信号时点；全球产量和库存按各国本地市场年度汇总，并非同一自然年/同一期末日。',
            '内外盘按自然月对照，各自交易日与收盘时刻不同；没有进行同一时刻对齐或汇率换算。窗口变化为首末月均价比，不是首末交易日收益。',
        ],
    )
