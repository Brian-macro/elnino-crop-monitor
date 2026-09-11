"""Production, geography, year and unit boundaries for national-source parsers."""
import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from local_sources import abares, bcr, conab, ec


@pytest.fixture
def observe(monkeypatch):
    def row(doc, crop, country, year, value, **kw):
        return dict(crop=crop, country=country, year=year, value=value, **kw)
    for module in (abares, bcr, conab, ec):
        monkeypatch.setattr(module, 'observation', row)


def ec_book(oilseeds=False, prior=True):
    kind = 'Production' if oilseeds else 'Gross production'
    cover = pd.DataFrame([
        ['Update:', datetime(2026, 8, 27), None],
        [kind + ' (thousand tonnes)', None, None],
        [('For all oilseeds:' if oilseeds else 'For all cereals:') + ' marketing year 1st July - 30th June', None, None],
        ['Crop', '2025f', '2026p'],
    ])
    geo = 'EU-27' if oilseeds else 'EU-27 (2020)'
    products = ['Soybean'] if oilseeds else ['Grain maize', 'Soft wheat', 'Durum wheat']
    data = pd.DataFrame([
        ['Type', 'Product', 'MS', 2025, 2026],
        *[[kind, product, geo, 7000 if prior else None, 8000 + i * 1000] for i, product in enumerate(products)],
        [kind, products[0], 'EU-28', 999999, 999999],
        ['Yield', products[0], geo, 900, 900],
    ])
    return {'Table&Graphs': cover, 'Data': data}


@pytest.mark.parametrize('oilseeds', [False, True])
def test_ec_real_workbook_structure(monkeypatch, observe, oilseeds):
    sheets = ec_book(oilseeds)
    payload = io.BytesIO()
    with pd.ExcelWriter(payload, engine='openpyxl') as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False, header=False)
    monkeypatch.setattr(ec, 'content', lambda doc: payload.getvalue())
    assert ec.resolve_date(payload.getvalue())['publication_date'] == '2026-08-27'
    result = ec.parse({})
    current = [r for r in result['forecast'] if r['year']==2026]
    assert [r['value'] for r in current] == ([8] if oilseeds else [8, 19])
    assert len([r for r in result['forecast'] if r['year']==2025]) == (1 if oilseeds else 2)
    assert result['estimate']==[]
    assert result['forecast'][0]['basis'] == ('oilseed' if oilseeds else 'grain')


def test_ec_current_without_prior(monkeypatch, observe):
    monkeypatch.setattr(ec, 'content', lambda doc: b'fixture')
    monkeypatch.setattr(ec.pd, 'read_excel', lambda *a, **kw: ec_book(prior=False))
    result = ec.parse({})
    assert len(result['forecast']) == 2
    assert result['estimate'] == []


@pytest.mark.parametrize('change', ['unit', 'geo', 'duplicate', 'missing_durum', 'nan', 'negative', 'status'])
def test_ec_rejects_invalid_contract(monkeypatch, observe, change):
    sheets = ec_book()
    if change == 'unit': sheets['Table&Graphs'].iat[1, 0] = 'Area (thousand hectares)'
    if change == 'geo': sheets['Data'].iat[1, 2] = 'EU-28'
    if change == 'duplicate': sheets['Data'] = pd.concat([sheets['Data'], sheets['Data'].iloc[[1]]])
    if change == 'missing_durum': sheets['Data'] = sheets['Data'].drop(index=3)
    if change == 'nan': sheets['Data'].iat[1, 4] = float('nan')
    if change == 'negative': sheets['Data'].iat[1, 4] = -1
    if change == 'status': sheets['Table&Graphs'].iat[3, 2] = '2026e'
    monkeypatch.setattr(ec, 'content', lambda doc: b'fixture')
    monkeypatch.setattr(ec.pd, 'read_excel', lambda *a, **kw: sheets)
    with pytest.raises(ValueError): ec.parse({})


def test_ec_discovers_gross_not_usable():
    html = '<a href="usable.xlsx">EU cereals production (usable), area and yield</a><a href="gross.xlsx">EU cereals production, area and yield</a>'
    assert ec.discover_html(html)[0]['url'].endswith('/gross.xlsx')
    with pytest.raises(ValueError): ec.discover_html(html.replace('EU cereals production,', 'Changed,'))


@pytest.mark.parametrize('value', ['28.4', '30.7'])
def test_abares_extracts_value_and_season_not_constant(monkeypatch, observe, value):
    html = f'<main><p>Wheat production is forecast to fall by 12.5% to {value} million tonnes in 2027-28.</p><p>Maize production is projected to rise to 450 thousand tonnes in 2027-28.</p></main>'
    monkeypatch.setattr(abares, 'content', lambda doc: html)
    rows = abares.parse({})
    assert [(r['crop'], r['year'], r['value']) for r in rows['forecast']] == [('corn', 2027, .45), ('wheat', 2027, float(value))]
    assert rows['estimate'] == []


@pytest.mark.parametrize('text', [
    'Wheat area is forecast to reach 29.9 million hectares in 2026-27.',
    'Wheat production was 29.9 million tonnes in 2026-27.',
    'Wheat production is forecast to reach 29.9 million tonnes.',
    'Wheat production is forecast to fall. Exports rise to 29.9 million tonnes in 2026-27.',
    'In Western Australia wheat production is forecast to reach 29.9 million tonnes in 2026-27.',
    'Wheat production is forecast to reach 29.9 million tonnes in 2026-28.',
    'Wheat production is forecast to reach 29.9 million tonnes in 2026-27, versus 2025-26.',
])
def test_abares_rejects_unbound_or_nonproduction_value(monkeypatch, observe, text):
    monkeypatch.setattr(abares, 'content', lambda doc: '<p>' + text + '</p>')
    with pytest.raises(ValueError): abares.parse({})


def test_abares_does_not_invent_publication_day():
    assert abares.resolve_date(b'<h1>September 2026</h1>')['publication_date'] is None
    assert abares.resolve_date(b'<meta property="article:published_time" content="2026-09-08T09:00:00Z">')['publication_date'] == '2026-09-08'


def test_conab_rice_keeps_paddy_and_original_year(monkeypatch, observe):
    sheets = {}
    for name in ['Milho Total', 'Soja', 'Trigo', 'Arroz Total']:
        years = ['Safra 2025', 'Safra 2026'] if name == 'Trigo' else ['Safra 24/25', 'Safra 25/26']
        sheets[name] = pd.DataFrame([[None, 'PRODUÇÃO (Em mil t)', None], [None, *years], ['BRASIL', 6000, 7000]])
    monkeypatch.setattr(conab, 'content', lambda doc: b'fixture')
    monkeypatch.setattr(conab.pd, 'read_excel', lambda *a, **kw: sheets)
    rows = conab.parse({})['forecast']
    assert [r['year'] for r in rows] == [2025, 2025, 2026, 2025]
    assert rows[-1]['basis'] == 'paddy'
    sheets['Arroz Total'].iat[2, 2] = float('nan')
    with pytest.raises(ValueError, match='invalid national production'): conab.parse({})


def test_bcr_rejects_duplicate_season(monkeypatch):
    row = '<tr><td>2026/2027</td><td></td><td></td><td>60 MILLONES TN</td></tr>'
    monkeypatch.setattr(bcr, 'content', lambda doc: '<table class="bcr-estimaciones maiz"><tbody>' + row * 2 + '</tbody></table>')
    with pytest.raises(ValueError, match='duplicate season'): bcr.parse({})


def test_bcr_requires_national_date_context():
    with pytest.raises(ValueError, match='heading'): bcr.resolve_date(b'09 de Septiembre de 2026')
