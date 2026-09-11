"""DG AGRI EU-27 gross cereal production from the official workbook data sheet."""
import io
import math
import re
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = 'ec'
URL = 'https://agriculture.ec.europa.eu/data-and-analysis/markets/overviews/market-observatories/crops/cereals-statistics_en'
OILSEEDS_URL = 'https://agriculture.ec.europa.eu/data-and-analysis/markets/overviews/market-observatories/crops/oilseeds-and-protein-crops_en'


def discover_html(payload, oilseeds=False):
    soup = BeautifulSoup(payload, 'html.parser')
    label = ('EU oilseeds and protein crops production, area and yield' if oilseeds
             else 'EU cereals production, area and yield')
    links = [a for a in soup.select('a[href]') if a.get_text(' ', strip=True) == label
             and a['href'].lower().endswith('.xlsx')]
    if len(links) != 1:
        raise ValueError('EC gross production workbook link missing or ambiguous')
    return [dict(url=urljoin(URL, links[0]['href']), title='DG AGRI ' + label, suffix='.xlsx')]


def discover():
    items = []
    for url, oilseeds in [(URL, False), (OILSEEDS_URL, True)]:
        response = requests.get(url, timeout=(10, 35))
        response.raise_for_status()
        items.extend(discover_html(response.content, oilseeds=oilseeds))
    return items


def resolve_date(payload):
    frame = pd.read_excel(io.BytesIO(payload), sheet_name='Table&Graphs', header=None)
    dates = []
    for row in frame.itertuples(index=False, name=None):
        for j, cell in enumerate(row[:-1]):
            if str(cell).strip() == 'Update:' and isinstance(row[j + 1], datetime):
                dates.append(row[j + 1].date().isoformat())
    if len(set(dates)) != 1:
        raise ValueError('EC workbook update date missing or ambiguous')
    return dict(publication_date=dates[0], date_basis='DG AGRI workbook Update cell')


def parse(doc):
    sheets = pd.read_excel(io.BytesIO(content(doc)), sheet_name=None, header=None)
    cover = sheets['Table&Graphs']
    text = ' '.join(str(v) for v in cover.to_numpy().ravel())
    oilseeds = 'For all oilseeds:' in text
    production_type = 'Production' if oilseeds else 'Gross production'
    if not (production_type.lower() in text.lower() and 'thousand tonnes' in text.lower()
            and 'marketing year 1st July - 30th June' in text):
        raise ValueError('EC gross production units or marketing-year definition missing')
    labelled = {int(m[1]): m[2] for v in cover.to_numpy().ravel()
                if (m := re.fullmatch(r'(20\d{2})([efp])', str(v).strip()))}
    if not labelled or labelled[max(labelled)] not in ('f', 'p'):
        raise ValueError('EC latest forecast/projection year missing')
    year = max(labelled)
    raw = sheets['Data']
    data = raw.iloc[1:].copy()
    data.columns = raw.iloc[0].tolist()
    geo = 'EU-27' if oilseeds else 'EU-27 (2020)'
    rows = data.loc[(data['Type'] == production_type) & (data['MS'] == geo)]
    out = {'forecast': [], 'estimate': []}
    crops = [('soybean', ['Soybean'])] if oilseeds else [('corn', ['Grain maize']), ('wheat', ['Soft wheat', 'Durum wheat'])]
    for crop, products in crops:
        selected = rows.loc[rows['Product'].isin(products)]
        if len(selected) != len(products) or set(selected['Product']) != set(products):
            raise ValueError('EC missing or duplicate EU-27 crop rows: ' + crop)
        for status, target in [('forecast', year), ('estimate', year - 1)]:
            if target not in data.columns or selected[target].isna().any():
                if status == 'estimate':
                    continue
                raise ValueError('EC current production missing: ' + crop)
            values = [float(v) for v in selected[target]]
            if any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError('EC invalid production value')
            status = 'forecast' if labelled.get(target) in ('f','p') else 'estimate'
            out[status].append(observation(doc, crop, 'European Union', target, sum(values) / 1000,
                basis='oilseed' if oilseeds else 'grain', year_basis='marketing_year', methodology=(
                    'DG AGRI EU-27 without UK, ' + production_type.lower() + '; ' + ' + '.join(products)
                    + '; thousand tonnes / 1000; year starts 1 July; source year flag=' + labelled.get(target,'unmarked') + '; not final actual')))
    return out
