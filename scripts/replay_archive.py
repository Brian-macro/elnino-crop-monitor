"""Rebuild from archived originals without network. Does not claim a fresh source check."""
import json,re,calendar,io,hashlib
from datetime import datetime
from pathlib import Path
from db import connect,insert_rows
from archive import archive_bytes,content,save_parsed
from config import RAW,ROOT
from fetch_china_outlook import parse_summary
from fetch_cropwatch import tables
from fetch_prices import main as prices_main
import pdfplumber
from bs4 import BeautifulSoup

def ingest_replay(con,meta,payload,parse,**date_evidence):
    sha=hashlib.sha256(payload).hexdigest()
    document_id=hashlib.sha256((meta['source']+meta['source_url']+sha).encode()).hexdigest()
    if sha!=meta['sha256'] or document_id!=meta['document_id']:
        raise ValueError('Archived document identity does not match its payload')
    con.execute('BEGIN')
    try:
        columns=['document_id','source','source_url','raw_path','sha256','publication_date','available_date','download_timestamp','publication_date_basis','title']
        con.execute('INSERT INTO source_documents ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+') ON CONFLICT DO NOTHING',
                    [meta[column] for column in columns])
        doc=archive_bytes(con,meta['source'],meta['source_url'],payload,Path(meta['raw_path']).suffix,**date_evidence)
        rows=parse(doc)
        insert_rows(con,rows,'forecast')
        # Date evidence applies to every existing interpretation of this document.
        for table in ('actual_production','forecast_production','estimated_production'):
            con.execute(f'UPDATE {table} SET publication_date=?,available_date=? WHERE document_id=?',
                        [doc['publication_date'],doc['available_date'],doc['document_id']])
        for table in ('climate','prices'):
            con.execute(f'UPDATE {table} SET available_date=? WHERE document_id=?',[doc['available_date'],doc['document_id']])
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK');raise
    save_parsed(doc,rows)
    return len(rows)

def record_replay_coverage(con,source,rows):
    con.execute('''INSERT INTO source_metadata(source,last_success,last_publication_date,status,error,rows_ingested)
      SELECT ?,max(download_timestamp),max(publication_date),'partial','Offline archive replay; live source availability has not been checked.',?
      FROM source_documents WHERE source=?
      ON CONFLICT(source) DO UPDATE SET rows_ingested=excluded.rows_ingested''',[source,rows,source])

def main():
    con=connect();cw=0;cn=0
    # Reconstruct report issue dates from the publisher's archived index.
    issues={}
    for p in (RAW/'cropwatch').glob('*.html'):
        soup=BeautifulSoup(p.read_bytes(),'html.parser')
        for a in soup.select('a[href]'):
            m=re.search(r'(\w+) (20\d{2}) CropWatch Bulletin',a.get_text())
            ident=re.search(r'id=(\d+)',a.get('href',''))
            if m and ident:
                try:issues[ident[1]]=(int(m[2]),datetime.strptime(m[1],'%B').month)
                except ValueError:pass
    for source in ('china_outlook','cropwatch'):
        archived=[json.loads(mp.read_text(encoding='utf-8')) for mp in (RAW/source).glob('*.metadata.json')]
        for meta in sorted(archived,key=lambda item:item['download_timestamp']):
            p=ROOT/meta['raw_path'];url=meta['source_url']
            try:
                if source=='china_outlook' and p.suffix=='.pdf':
                    with pdfplumber.open(p) as pdf:text='\n'.join(x.extract_text() or '' for x in pdf.pages)
                    compact=re.sub(r'\s+','',text)
                    if '今年4月20日发布' not in compact or '2026' not in compact:continue
                    cn+=ingest_replay(con,meta,p.read_bytes(),lambda d:parse_summary(text,d,2026),publication_date='2026-04-20',date_basis='PDF preface explicitly states release date',title='China Agricultural Outlook 2026 summary')
                elif source=='cropwatch' and p.suffix=='.html' and 'sectionId=' in url:
                    match=re.search(r'id=(\d+)',url)
                    if not match or match[1] not in issues:continue
                    year,month=issues[match[1]];available=f'{year}-{month:02d}-{calendar.monthrange(year,month)[1]}'
                    cw+=ingest_replay(con,meta,p.read_bytes(),lambda d:tables(d,year),available_date=available,date_basis='Issue month from archived official index; conservative month-end availability',title=f'CropWatch {year}-{month:02d}')
            except Exception as e:print('Archive replay issue',url,e)
    for source,n in [('china_outlook',cn),('cropwatch',cw)]:
        if n:
            record_replay_coverage(con,source,n)
    print('Archive replay: China Outlook',cn,'CropWatch',cw)
    con.close()
if __name__=='__main__':main()
