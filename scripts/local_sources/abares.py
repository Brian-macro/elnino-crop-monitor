"""ABARES national crop projections; require explicit crop, production, year and unit."""
import re
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from archive import content, observation

SOURCE = 'abares'
URL = 'https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook/australian-crop-report'


def discover():
    response = requests.get(URL, timeout=(10, 35))
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    links = {urljoin(URL, a['href']) for a in soup.select('a[href]')
             if a.get_text(' ', strip=True).lower() in ('national overview', 'overview')
             and 'australian-crop-report' in urljoin(URL, a['href'])}
    if len(links) > 1:
        raise ValueError('ABARES national overview link ambiguous')
    return [dict(url=next(iter(links), URL), title='ABARES Australian Crop Report national overview', suffix='.html')]


def resolve_date(payload):
    soup = BeautifulSoup(payload, 'html.parser')
    stamps = {m.get('content', '')[:10] for m in soup.select(
        'meta[property="article:published_time"], meta[name="dcterms.issued"], meta[itemprop="datePublished"]')}
    if len(stamps) == 1:
        stamp = date.fromisoformat(stamps.pop()).isoformat()
        return dict(publication_date=stamp, date_basis='ABARES page publication metadata')
    return dict(publication_date=None, date_basis='unknown; first observed; report month is not a publication day')


def parse(doc):
    soup = BeautifulSoup(content(doc), 'html.parser')
    root = soup.find('main') or soup
    found = {}
    for block in root.select('p, li'):
        text = block.get_text(' ', strip=True)
        # A year elsewhere on the page could describe the previous crop or a state.
        seasons = re.findall(r'\b(20\d{2})[-/\u2013](\d{2}|20\d{2})\b', text)
        if len(set(seasons)) != 1:
            continue
        first, last = seasons[0]
        year = int(first)
        if int(last) % 100 != (year + 1) % 100:
            raise ValueError('ABARES non-consecutive crop season')
        if re.search(r'\b(?:New South Wales|Queensland|Victoria|Tasmania|South Australia|Western Australia)\b', text, re.I):
            continue
        for crop, name, basis in [('wheat', 'wheat', 'grain'), ('corn', '(?:maize|corn)', 'grain'), ('soybean', 'soybeans?', 'oilseed')]:
            pattern = (rf'\b{name}\s+production\s+is\s+(?:forecast|expected|projected)\b'
                       rf'(?:(?!;|\.(?:\s|$)|\b(?:area|yield|exports|consumption|barley|canola)\b).){{0,180}}?'
                       rf'\b(?:to|at)\s+([0-9]+(?:\.[0-9]+)?)\s+(million|thousand)\s+tonnes\b')
            for match in re.finditer(pattern, text, re.I):
                value = float(match[1]) / (1000 if match[2].lower() == 'thousand' else 1)
                key = (crop, year)
                if key in found and found[key][0] != value:
                    raise ValueError('ABARES conflicting national projections: ' + crop)
                found[key] = (value, basis)
    if not found:
        raise ValueError('ABARES explicit national crop production forecast/year/unit not found')
    rows = [observation(doc, crop, 'Australia', year, value, basis=basis,
            year_basis='marketing_year', methodology='ABARES national overview; explicit production projection and crop season; start year; no inferred prior')
            for (crop, year), (value, basis) in sorted(found.items())]
    return {'forecast': rows, 'estimate': []}
