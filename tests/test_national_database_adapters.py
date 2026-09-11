import importlib
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def document(source):
    docs=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'data'/'raw'/source).glob('*.metadata.json')]
    return max(docs,key=lambda d:d['download_timestamp'])


@pytest.mark.parametrize('source,country',[
    ('us_nass','United States'),('uk_defra','United Kingdom'),('mx_siap','Mexico'),
    ('jp_maff','Japan'),('ph_psa','Philippines'),('my_dosm','Malaysia'),
    ('pk_pbs','Pakistan'),('tw_afa','Taiwan'),('kz_bns','Kazakhstan')])
def test_archived_national_database_remains_parseable_without_regional_double_count(source,country):
    batch=importlib.import_module('local_sources.'+source).parse(document(source))
    rows=[r for observations in batch.values() for r in observations]
    assert rows and {r['country'] for r in rows}=={country}
    assert all(r['region']=='' and r['unit']=='Mt' for r in rows)
    keys=[(r['crop'],r['target_year'],r['commodity_basis']) for r in rows]
    assert len(keys)==len(set(keys))


def test_psa_rejects_subnational_totals_and_excludes_open_year(monkeypatch):
    from local_sources import ph_psa
    doc=document('ph_psa')
    rows=ph_psa.parse(doc)['estimate']
    assert all(r['target_year']<int(doc['available_date'][:4]) for r in rows)
    payload=(ROOT/doc['raw_path']).read_bytes().replace(b'PHILIPPINES',b'Region I')
    monkeypatch.setattr(ph_psa,'content',lambda d:payload)
    with pytest.raises(ValueError,match='national crop totals'):
        ph_psa.parse(doc)


def test_refined_sugar_and_paddy_are_never_relabelled_as_raw_sugar_or_milled_rice():
    from local_sources import uk_defra,my_dosm
    sugar=[r for r in uk_defra.parse(document('uk_defra'))['estimate'] if r['crop']=='sugar']
    rice=my_dosm.parse(document('my_dosm'))['estimate']
    assert sugar and all(r['commodity_basis']=='refined' for r in sugar)
    assert rice and all(r['commodity_basis']=='paddy' for r in rice)
