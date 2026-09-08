"""Descriptive monthly price research. Missing observations never become prices."""
from collections import defaultdict
import math
import numpy as np

def month_index(month):
    y,m=map(int,month[:7].split('-'));return y*12+m-1

def month_label(index):
    y,m=divmod(index,12);return f'{y:04d}-{m+1:02d}'

def monthly_prices(rows):
    groups=defaultdict(list)
    for r in rows:
        if r['value'] is not None and math.isfinite(r['value']):groups[r['date'][:7]].append(r['value'])
    return {m:float(np.mean(v)) for m,v in sorted(groups.items())}

def monthly_returns(months):
    return {m:100*(v/months[month_label(month_index(m)-1)]-1) for m,v in months.items()
        if months.get(month_label(month_index(m)-1),0)>0}

def correlation(a,b,minimum=12):
    if len(a)<minimum or len(a)!=len(b) or np.std(a)==0 or np.std(b)==0:return None
    return float(np.corrcoef(a,b)[0,1])

def event_prices(rows,anchor):
    idx=month_index(anchor);months=monthly_prices(rows)
    values=[v for m,v in months.items() if idx-12<=month_index(m)<=idx+12]
    if len(values)<2:return dict(change_pct=None,max_drawdown_pct=None,maximum_rally_pct=None,observations=len(values))
    peak=low=values[0];dd=rally=0
    for v in values:
        peak=max(peak,v);low=min(low,v);dd=min(dd,(v/peak-1)*100);rally=max(rally,(v/low-1)*100)
    return dict(change_pct=round((values[-1]/values[0]-1)*100,8),max_drawdown_pct=dd,maximum_rally_pct=rally,observations=len(values))

def price_research(rows):
    series={market:monthly_prices([r for r in rows if r['market']==market]) for market in ('china','overseas')}
    all_months=sorted(set(series['china'])|set(series['overseas']))
    end=month_index(all_months[-1]) if all_months else 0;ranges={}
    rets={market:monthly_returns(values) for market,values in series.items()}
    for label,window in [('1Y',12),('3Y',36),('5Y',60),('10Y',120),('Full',10000)]:
        months=[m for m in all_months if month_index(m)>end-window]
        aligned=[m for m in months if m in series['china'] and m in series['overseas']]
        paired=[m for m in months if all(m in r for r in rets.values())]
        leadlag=[]
        for lag in range(-6,7):
            pairs=[(rets['china'][m],rets['overseas'][month_label(month_index(m)-lag)]) for m in months
                if m in rets['china'] and month_label(month_index(m)-lag) in rets['overseas'] and month_label(month_index(m)-lag) in months]
            leadlag.append(dict(lag=lag,n=len(pairs),correlation=correlation([a for a,b in pairs],[b for a,b in pairs])))
        rolling=[]
        for m in months:
            candidates=[month_label(i) for i in range(month_index(m)-11,month_index(m)+1)]
            p=[t for t in candidates if t in months and all(t in r for r in rets.values())]
            rolling.append(dict(month=m,n=len(p),value=correlation([rets['china'][t] for t in p],[rets['overseas'][t] for t in p])))
        ranges[label]=dict(paired_months=len(aligned),return_pairs=len(paired),index_base=aligned[0] if aligned else None,
            correlation=correlation([rets['china'][m] for m in paired],[rets['overseas'][m] for m in paired]),rolling=rolling,leadlag=leadlag)
    return dict(monthly=series,ranges=ranges,methodology='Observed monthly means; NBS is a partial ten-day survey sample. Correlation uses changes in consecutive monthly mean quotes (not investable returns), minimum 12 pairs. Positive lag means overseas leads China. No gap filling; no common closing-time or FX adjustment.')
