import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

def test_old_psd_not_promoted_to_actual():
    import normalize
    assert hasattr(normalize, 'classify_psd'), 'PSD needs a vintage-relative classifier'
    assert normalize.classify_psd(2015, '2026-08-12') == 'estimate'
    assert normalize.classify_psd(2015, '2015-08-12') == 'forecast'

def test_real_separate_tables():
    import db
    assert 'CREATE TABLE IF NOT EXISTS actual_production' in db.DDL
    assert 'CREATE TABLE IF NOT EXISTS forecast_production' in db.DDL
    assert 'CREATE TABLE IF NOT EXISTS estimated_production' in db.DDL

def test_publication_date_not_invented():
    import db
    assert 'source_documents' in db.DDL

def test_asof_and_definition_contract():
    import db
    assert 'available_date' in db.DDL
    assert 'commodity_basis' in db.DDL
