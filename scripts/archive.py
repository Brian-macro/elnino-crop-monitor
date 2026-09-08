"""Content-addressed immutable downloads; append-only source ledger and parsed snapshots."""
import hashlib
import json
import os
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlparse
import requests
from config import ROOT, RAW, VINTAGE
from db import mark_source

def now():
    return datetime.now(timezone.utc).isoformat()

def archive_bytes(con, source, url, content, suffix='', publication_date=None, date_basis='unknown; first observed', title='', available_date=None):
    pub = date.fromisoformat(str(publication_date)[:10]) if publication_date else None
    available = date.fromisoformat(str(available_date)[:10]) if available_date else None
    if any(day and day > date.today() for day in (pub,available)):
        raise ValueError('Future source date rejected')
    if pub and available and available < pub:
        raise ValueError('Availability cannot precede publication')
    sha = hashlib.sha256(content).hexdigest()
    doc_id = hashlib.sha256((source+url+sha).encode()).hexdigest()
    old = con.execute('SELECT * FROM source_documents WHERE document_id=?',[doc_id]).fetchone()
    if old:
        names = [x[0] for x in con.description]
        result=dict(zip(names,old))
        # A descriptive issue-month label is not proof that an availability date
        # was actually recorded. Preserve the original metadata and append evidence.
        unknown_date=result['publication_date'] is None and str(result['available_date'])==str(result['download_timestamp'])[:10]
        has_evidence=(pub or available) and not date_basis.lower().startswith('unknown')
        if has_evidence and (unknown_date or result['publication_date_basis'].startswith('unknown')):
            correction=con.execute('SELECT count(*) FROM source_documents WHERE source=? AND source_url=? AND download_timestamp<?',[source,url,result['download_timestamp']]).fetchone()[0]>0
            correction=correction or 'content correction first observed' in result['publication_date_basis']
            effective=str(result['available_date']) if correction else str(available or pub)
            updated={**result,'publication_date':str(pub) if pub else result['publication_date'],'available_date':effective,
                     'publication_date_basis':date_basis+('; content correction first observed' if correction else '')}
            payload=json.dumps({'before':result,'after':updated},default=str,ensure_ascii=False,sort_keys=True)
            evidence=RAW/source/(sha+'.date-evidence-'+hashlib.sha256(payload.encode()).hexdigest()[:12]+'.json')
            if not evidence.exists():evidence.write_text(payload,encoding='utf-8')
            con.execute('UPDATE source_documents SET publication_date=?,available_date=?,publication_date_basis=? WHERE document_id=?',
                        [updated['publication_date'],effective,updated['publication_date_basis'],doc_id])
            result=updated
        return result
    stamp=now()
    path=RAW/source/(sha+(suffix or Path(urlparse(url).path).suffix or '.html'))
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    correction=con.execute('SELECT count(*) FROM source_documents WHERE source=? AND source_url=?',[source,url]).fetchone()[0]>0
    effective=stamp[:10] if correction else str(available or pub or date.today())
    doc=dict(document_id=doc_id,source=source,source_url=url,raw_path=str(path.relative_to(ROOT)).replace('\\','/'),
             sha256=sha,publication_date=str(pub) if pub else None,
             available_date=effective,download_timestamp=stamp,
             publication_date_basis=date_basis+('; content correction first observed' if correction else ''),title=title)
    path.with_name(sha+'.metadata.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    con.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)',list(doc.values()))
    return doc

def download(con, source, url, date_resolver=None, **kwargs):
    if os.environ.get('MONITOR_OFFLINE')=='1':
        found=[]
        for path in (RAW/source).glob('*.metadata.json'):
            meta=json.loads(path.read_text(encoding='utf-8'))
            if meta['source_url']==url:found.append(meta)
        if not found:raise ValueError('No archived original for '+url)
        meta=max(found,key=lambda x:x['download_timestamp']);payload=(ROOT/meta['raw_path']).read_bytes()
    else:
        response=requests.get(url,timeout=(10,35))
        response.raise_for_status();payload=response.content
    if date_resolver:kwargs.update(date_resolver(payload))
    return archive_bytes(con,source,url,payload,**kwargs)

def content(doc):
    return (ROOT/doc['raw_path']).read_bytes()

def save_parsed(doc, rows):
    path=VINTAGE/doc['source']/(doc['document_id']+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    # Parser revisions must never overwrite an earlier interpretation.
    payload=json.dumps(rows,ensure_ascii=False,default=str,allow_nan=False)
    path=path.with_name(path.stem+'-'+hashlib.sha256(payload.encode()).hexdigest()[:12]+'.json')
    if not path.exists(): path.write_text(payload,encoding='utf-8')

def observation(doc,crop,country,year,value,metric='production',unit='Mt',basis='grain',year_basis='marketing_year',region='',methodology='Official forecast'):
    return dict(document_id=doc['document_id'],crop=crop,country=country,region=region,target_year=int(year),
                year_basis=year_basis,commodity_basis=basis,metric=metric,value=float(value),unit=unit,
                source=doc['source'],publication_date=doc['publication_date'],available_date=doc['available_date'],
                download_timestamp=doc['download_timestamp'],methodology=methodology,source_url=doc['source_url'])

def failed(con,source,error):
    mark_source(con,source,False,error=str(error)[:1500])
    print(f'[{source}] DATA STALE: {error}')
