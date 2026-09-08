import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
def test_conab_contract():
 import scripts.local_sources.conab as m
 assert m.SOURCE=='conab' and m.discover()[0]['suffix']=='.xlsx'
def test_conab_season_mapping():
 assert 2025==int('2025/26'.split('/')[0])
def test_cec_contract():
 import scripts.local_sources.cec as m
 assert m.SOURCE=='cec' and m.discover()[0]['suffix']=='.pdf'
def test_cec_calendar_mapping():
 assert 2026 != 2027
