"""Parse official WASDE text tables, preserving each monthly issue. No fake historical PSD vintages."""
import re,calendar,argparse
from datetime import date
from db import connect,insert_rows,mark_source
from archive import download,content,observation,save_parsed,failed
from config import COUNTRIES,BASIS
MONTHS=list(calendar.month_abbr)
# Exact dates verified in USDA 2026 release calendar; other years use conservative month-end availability.
RELEASE_2026={1:12,2:10,3:10,4:9,5:12,6:11,7:10,8:12,9:11,10:9,11:10,12:10}

def parse_wasde(text,doc,month):
    out={'forecast':[],'estimate':[]}
    crop=None;year=None;status=None;country=None
    supported=set(COUNTRIES+['World','United Kingdom','Japan','Burma','Egypt','Nigeria'])
    for line in text.splitlines():
        title=re.search(r'World (Wheat|Corn|Rice|Soybean) Supply and Use',line)
        if title:
            crop=title[1].lower();country=None;year=None;continue
        if 'WASDE -' in line:crop=None;year=None;continue
        if not crop:continue
        yr=re.match(r'^\s+(\d{4})/\d{2}(?:\s+(Est\.|Proj\.))?\s*$',line)
        if yr:
            year=int(yr[1]);status='forecast' if yr[2]=='Proj.' else 'estimate';continue
        if year is None:continue
        nums=re.findall(r'-?\d+\.\d+',line)
        prefix=re.split(r'-?\d+\.\d+',line)[0].strip()
        label=re.sub(r'\s+\d+/', '',prefix).strip()
        mon=next((m for m in MONTHS[1:] if re.search(r'\b'+m+r'\b',label)),None)
        label=re.sub(r'\b(?:'+ '|'.join(MONTHS[1:])+r')\b','',label).strip()
        if label:country=label
        if country not in supported:continue
        if mon and mon!=MONTHS[month]:continue # previous month's column is not a newly known old vintage
        if not nums:continue
        metrics=['beginning_stocks','production','imports','consumption','exports','ending_stocks'] if crop=='rice' else ['beginning_stocks','production','imports','crush' if crop=='soybean' else 'feed','consumption','exports','ending_stocks']
        if len(nums)!=len(metrics):continue
        for metric,val in zip(metrics,nums):
            out[status].append(observation(doc,crop,'Global' if country=='World' else country,year,val,metric,basis=BASIS[crop],methodology='WASDE published table: '+('Proj.' if status=='forecast' else 'historical/Est.; not final actual')))
    if not all(any(r['country']=='Global' and r['crop']==cr and r['metric']=='production' for rs in out.values() for r in rs) for cr in ['corn','wheat','rice','soybean']):
        raise ValueError('WASDE layout changed: missing required World production rows')
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--months',type=int,default=16);args=ap.parse_args()
    con=connect();today=date.today();n=0;errors=[];latest=None
    for offset in reversed(range(args.months)):
        idx=today.year*12+today.month-1-offset;year,zero=divmod(idx,12);month=zero+1
        day=RELEASE_2026[month] if year==2026 else calendar.monthrange(year,month)[1]
        pub=date(year,month,day)
        if pub>today:continue
        url=f'https://www.usda.gov/oce/commodity/wasde/wasde{month:02d}{year%100:02d}.txt'
        try:
            doc=download(con,'usda_wasde',url,suffix='.txt',publication_date=pub.isoformat() if year==2026 else None,
               date_basis='USDA release calendar' if year==2026 else 'report month; conservative month-end available date',title=f'WASDE {year}-{month:02d}',available_date=pub.isoformat())
            text=content(doc).decode('utf-8',errors='replace')
            batches=parse_wasde(text,doc,month)
            con.execute('BEGIN')
            try:
                for kind,rows in batches.items():insert_rows(con,rows,kind);n+=len(rows)
                con.execute('COMMIT')
            except Exception:con.execute('ROLLBACK');raise
            save_parsed(doc,batches);latest=pub.isoformat();print('WASDE',pub,sum(map(len,batches.values())))
        except Exception as e:errors.append(f'{year}-{month}: {e}');print(errors[-1])
    if latest:mark_source(con,'usda_wasde',True,latest,rows=n,status='partial' if errors else 'ok',error='; '.join(errors) or None)
    else:failed(con,'usda_wasde','; '.join(errors))
    con.close();return 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
