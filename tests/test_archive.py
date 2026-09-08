import sys
from pathlib import Path
from datetime import date
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

def test_same_url_correction_never_backdates(tmp_path,monkeypatch):
    import archive
    from db import connect
    monkeypatch.setattr(archive,'RAW',tmp_path/'raw');monkeypatch.setattr(archive,'ROOT',tmp_path)
    con=connect(':memory:')
    old=archive.archive_bytes(con,'test','https://example.org/report',b'old','.txt',publication_date='2025-01-10')
    new=archive.archive_bytes(con,'test','https://example.org/report',b'correction','.txt',publication_date='2025-01-10')
    assert old['document_id']!=new['document_id']
    assert str(new['available_date'])==date.today().isoformat()
    assert str(old['available_date'])=='2025-01-10'
    assert con.execute('select count(*) from source_documents').fetchone()[0]==2
    con.close()


def test_issue_month_evidence_enriches_only_initial_metadata(tmp_path,monkeypatch):
    import archive
    from db import connect
    monkeypatch.setattr(archive,'RAW',tmp_path/'raw');monkeypatch.setattr(archive,'ROOT',tmp_path)
    con=connect(':memory:')
    original=archive.archive_bytes(con,'test','https://example.org/report',b'original','.txt',date_basis='Issue month only; availability conservatively month-end')
    metadata=tmp_path/'raw'/'test'/(original['sha256']+'.metadata.json')
    before=metadata.read_bytes()
    enriched=archive.archive_bytes(con,'test','https://example.org/report',b'original','.txt',available_date='2025-12-31',date_basis='Issue month from archived official index; conservative month-end availability')
    assert str(enriched['available_date'])=='2025-12-31'
    assert metadata.read_bytes()==before, 'Original archive metadata must remain immutable'
    audits=list(metadata.parent.glob('*.date-evidence*.json'))
    assert len(audits)==1
    audit=json.loads(audits[0].read_text(encoding='utf-8'))
    assert audit['before']['available_date']==date.today().isoformat()
    assert audit['after']['available_date']=='2025-12-31'
    con.close()


def test_later_date_evidence_does_not_backdate_correction(tmp_path,monkeypatch):
    import archive
    from db import connect
    monkeypatch.setattr(archive,'RAW',tmp_path/'raw');monkeypatch.setattr(archive,'ROOT',tmp_path)
    con=connect(':memory:')
    archive.archive_bytes(con,'test','https://example.org/report',b'original','.txt')
    archive.archive_bytes(con,'test','https://example.org/report',b'corrected','.txt')
    corrected=archive.archive_bytes(con,'test','https://example.org/report',b'corrected','.txt',publication_date='2025-12-15',date_basis='Official report release date')
    assert str(corrected['available_date'])==date.today().isoformat()
    con.close()


def test_replay_syncs_dates_and_preserves_live_failure(tmp_path,monkeypatch):
    import archive,replay_archive
    from db import connect,insert_rows,mark_source
    monkeypatch.setattr(archive,'RAW',tmp_path/'raw');monkeypatch.setattr(archive,'ROOT',tmp_path)
    monkeypatch.setattr(archive,'VINTAGE',tmp_path/'vintage')
    con=connect(':memory:')
    doc=archive.archive_bytes(con,'cropwatch','https://example.org/report',b'original','.txt',date_basis='Issue month only; availability conservatively month-end')
    insert_rows(con,[archive.observation(doc,'corn','China',2025,10)],'forecast')
    mark_source(con,'cropwatch',False,error='Live request timed out')
    before=con.execute('select last_checked,last_success,status,error from source_metadata').fetchone()
    assert hasattr(replay_archive,'ingest_replay'), 'Replay needs a transactional document and observation update'
    replay_archive.ingest_replay(con,doc,b'original',lambda d:[archive.observation(d,'corn','China',2025,10)],available_date='2025-12-31',date_basis='Archived issue index month-end')
    replay_archive.record_replay_coverage(con,'cropwatch',1)
    assert con.execute('select last_checked,last_success,status,error from source_metadata').fetchone()==before
    assert con.execute('select count(*) from forecast_production').fetchone()[0]==1
    assert str(con.execute('select available_date from forecast_production').fetchone()[0])=='2025-12-31'
    assert con.execute('select count(*) from forecast_production p join source_documents d using(document_id) where p.available_date<>d.available_date').fetchone()[0]==0
    con.close()


def test_first_offline_replay_has_no_live_check_timestamp():
    import replay_archive
    from db import connect
    con=connect(':memory:')
    assert hasattr(replay_archive,'record_replay_coverage'), 'Offline replay status must not claim a live check'
    replay_archive.record_replay_coverage(con,'cropwatch',3)
    checked,status,error,rows=con.execute('select last_checked,status,error,rows_ingested from source_metadata').fetchone()
    assert checked is None and status=='partial' and 'offline' in error.lower() and rows==3
    con.close()


def test_replay_into_empty_store_preserves_archived_metadata(tmp_path,monkeypatch):
    import archive,replay_archive
    from db import connect
    monkeypatch.setattr(archive,'RAW',tmp_path/'raw');monkeypatch.setattr(archive,'ROOT',tmp_path)
    monkeypatch.setattr(archive,'VINTAGE',tmp_path/'vintage')
    origin=connect(':memory:')
    archive.archive_bytes(origin,'cropwatch','https://example.org/report',b'original','.txt')
    meta=archive.archive_bytes(origin,'cropwatch','https://example.org/report',b'correction','.txt')
    metadata=tmp_path/'raw'/'cropwatch'/(meta['sha256']+'.metadata.json')
    before=metadata.read_bytes();origin.close()
    con=connect(':memory:')
    replay_archive.ingest_replay(con,meta,b'correction',lambda d:[archive.observation(d,'corn','China',2025,11)],publication_date='2025-12-15',date_basis='Official report release date')
    assert metadata.read_bytes()==before
    row=con.execute('select download_timestamp,available_date from source_documents').fetchone()
    assert str(row[0])[:19]==meta['download_timestamp'][:19].replace('T',' ')
    assert str(row[1])==date.today().isoformat()
    con.close()
