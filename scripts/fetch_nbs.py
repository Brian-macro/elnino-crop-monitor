"""NBS official output anchors and ten-day domestic price observations. Grain totals are NOT crop-level province data."""
import argparse,re,io,hashlib,calendar
from urllib.parse import urljoin
import pandas as pd
from bs4 import BeautifulSoup
from archive import download,content,observation,save_parsed,failed
from db import connect,insert_rows,mark_source
NBS_ACTUAL=['https://www.stats.gov.cn/sj/zxfb/202512/t20251212_1962049.html']

def pubdate(url):
    m=re.search(r't(\d{4})(\d{2})(\d{2})_',url)
    if not m:raise ValueError('No official dated URL')
    return '-'.join(m.groups())

def parse_actuals(doc):
    soup=BeautifulSoup(content(doc),'html.parser')
    title=soup.title.get_text() if soup.title else ''
    match=re.search(r'(20\d{2})年',title)
    if not match:raise ValueError('NBS bulletin has no explicit target year')
    year=int(match[1]);rows={}
    for table in soup.select('table'):
        df=pd.read_html(io.StringIO(str(table)))[0]
        if len(df.columns)!=4:continue
        header=re.sub(r'\s+','',str(df.iloc[0].tolist()))
        if not all(unit in header for unit in ['千公顷','万吨','公斤/公顷']):continue
        for _,row in df.iterrows():
            label=re.sub(r'\s+','',str(row.iloc[0]))
            label=re.sub(r'^其中[：:]', '',label)
            crop={'稻谷':'rice','小麦':'wheat','玉米':'corn','大豆':'soybean'}.get(label)
            if not crop:continue
            for col,metric,unit,div in [(2,'production','Mt',100),(1,'area','Mha',1000),(3,'yield','t/ha',1000)]:
                value=pd.to_numeric(row.iloc[col],errors='coerce')
                if pd.isna(value):continue
                record=observation(doc,crop,'China',year,value/div,metric,unit,basis='paddy' if crop=='rice' else 'oilseed' if crop=='soybean' else 'grain',year_basis='calendar_year',methodology='Official reported actual: NBS annual crop-output bulletin; source may later revise')
                key=(crop,metric)
                if key in rows and rows[key]['value']!=record['value']:
                    raise ValueError('Conflicting NBS bulletin tables: '+str(key))
                rows[key]=record
    if not {'rice','corn','wheat'}.issubset({r['crop'] for r in rows.values() if r['metric']=='production'}):
        raise ValueError('NBS actual parser missing required cereal production rows')
    return list(rows.values())

def parse_prices(doc):
    soup=BeautifulSoup(content(doc),'html.parser');title=soup.title.get_text() if soup.title else ''
    match=re.search(r'(20\d{2})年(\d+)月([上中下])旬',title)
    if not match:return []
    year,month,period=match.groups();end={'上':10,'中':20,'下':calendar.monthrange(int(year),int(month))[1]}[period]
    day=f'{year}-{int(month):02d}-{end:02d}';rows={}
    for table in soup.select('table'):
        df=pd.read_html(io.StringIO(str(table)))[0]
        if len(df.columns)!=5:continue
        for _,row in df.iterrows():
            label=str(row.iloc[0]);crop=next((c for k,c in [('小麦','wheat'),('玉米','corn'),('大豆','soybean'),('稻米','rice')] if label.startswith(k)),None)
            value=pd.to_numeric(row.iloc[2],errors='coerce')
            if not crop or pd.isna(value):continue
            if str(row.iloc[1]).strip()!='吨':raise ValueError('Unexpected NBS price unit: '+str(row.iloc[1]))
            record=dict(record_id=hashlib.sha256((doc['document_id']+crop).encode()).hexdigest(),document_id=doc['document_id'],crop=crop,market='china',symbol=label,date=day,value=float(value),currency='CNY',unit='CNY/t',price_type='NBS 10-day market survey; processing grade',source='china_prices',available_date=str(doc['available_date']))
            if crop in rows and (rows[crop]['value'],rows[crop]['symbol'])!=(record['value'],label):
                raise ValueError('Conflicting NBS price quotes for '+crop)
            rows[crop]=record
    return list(rows.values())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pages',type=int,default=6);args=ap.parse_args()
    con=connect();price_rows=[];actuals=[];issues=[]
    try:
        for url in NBS_ACTUAL:
            d=download(con,'nbs',url,suffix='.html',publication_date=pubdate(url),date_basis='Official dated release URL')
            batch=parse_actuals(d);actuals.extend(batch);save_parsed(d,batch)
        insert_rows(con,actuals,'actual')
        missing_soybean=not any(r['crop']=='soybean' for r in actuals)
        mark_source(con,'nbs',True,rows=len(actuals),pub_date=max(pubdate(u) for u in NBS_ACTUAL),
                    status='partial' if missing_soybean else 'ok',error='Annual cereal bulletin has no separate soybean output; beans total is not soybean.' if missing_soybean else None)
    except Exception as e:failed(con,'nbs',e);issues.append(str(e))
    try:
        links={'https://www.stats.gov.cn/sj/zxfbhjd/202608/t20260813_1965025.html'}
        for page in range(args.pages):
            url='https://www.stats.gov.cn/sj/zxfb/'+('index.html' if page==0 else f'index_{page}.html')
            try:
                d=download(con,'china_prices',url,suffix='.html')
                soup=BeautifulSoup(content(d),'html.parser')
                links.update(urljoin(url,a['href']) for a in soup.select('a[href]') if '流通领域' in a.get_text() and '市场价格变动情况' in a.get_text())
            except Exception as e:issues.append(str(e))
        for url in sorted(links):
            try:
                pub=pubdate(url);d=download(con,'china_prices',url,suffix='.html',publication_date=pub,date_basis='Official release URL')
                batch=parse_prices(d)
                if batch:save_parsed(d,batch);price_rows.extend(batch)
            except Exception as e:issues.append(str(e))
        if not price_rows:raise ValueError('NBS price layout changed or no supported quotes')
        con.register('_p',pd.DataFrame(price_rows));con.execute('INSERT INTO prices BY NAME SELECT * FROM _p ON CONFLICT DO NOTHING')
        mark_source(con,'china_prices',True,max(r['available_date'] for r in price_rows),observation_date=max(r['date'] for r in price_rows),rows=len(price_rows),status='partial',error='Short history; sugar unavailable. '+'; '.join(issues)[:600])
        print('NBS',len(actuals),'actual metrics,',len(price_rows),'domestic quotes')
    except Exception as e:failed(con,'china_prices',e);issues.append(str(e))
    con.close();return 2 if issues else 0
if __name__=='__main__':raise SystemExit(main())
