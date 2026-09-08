"""CropWatch discovery and source-table parsing, including reviewed image tables."""
import argparse
import calendar
import hashlib
import io
import re
from datetime import datetime, date
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from archive import download, content, observation, save_parsed, failed
from db import connect, insert_rows, mark_source
from config import BASIS


# Transcribed from the archived originals, visually checked on 2026-09-08.
# Tuples are (published 2025 quantity, 2026 quantity, published YoY%).
# Blank cells are absent. These selected Asian rows are not whole-world coverage.
IMAGE_TABLES = {
    '50c19a95f24f8a6e0ecf2bfc7e83e0d154feb28e4cc40cbd161f7ff161331121': {
        'appendix': 'http://cloud.cropwatch.com.cn/web/report/detail?id=325&sectionId=7972',
        'unit_source': 'http://cloud.cropwatch.com.cn/web/report/detail?id=325&sectionId=7944',
        'rows': {
            'China': {'corn': (263.45, 266.18, 1.0), 'rice': (211.33, 210.05, -0.6),
                      'wheat': (139.32, 140.96, 1.2), 'soybean': (19.26, 19.67, 2.1)},
            'Cambodia': {'rice': (10.39, 9.84, -5.2)},
            'Indonesia': {'corn': (18.14, 19.51, 7.6), 'rice': (67.94, 71.74, 5.6)},
            'Mongolia': {'wheat': (0.33, 0.41, 24.2)},
            'Myanmar': {'rice': (22.01, 20.75, -5.7)},
            'Philippines': {'corn': (7.11, 6.92, -2.7), 'rice': (20.94, 20.51, -2.1)},
            'Thailand': {'corn': (3.44, 3.52, 2.6), 'rice': (37.41, 39.18, 4.7)},
            'Vietnam': {'corn': (4.04, 4.17, 3.2), 'rice': (47.82, 47.26, -1.2)},
            'Laos': {'rice': (3.82, 3.92, 2.6)},
            'Bangladesh': {'corn': (3.59, 3.28, -8.6), 'rice': (46.573, 46.855, 0.6)},
            'India': {'corn': (42.89, 53.01, 23.6), 'rice': (213.42, 192.91, 9.6),
                      'wheat': (118.16, 116.85, -6.1), 'soybean': (13.06, 12.36, -5.3)},
            'Pakistan': {'corn': (6.39, 6.65, 4.1), 'rice': (13.471, 13.27, -1.5),
                         'wheat': (24.84, 22.94, -7.6)},
            'Sri Lanka': {'rice': (2.39, 2.48, 3.7)},
        },
    },
    '2ec99b42d2cb2400d3fd9cf24bd9e1b8951f9af7d0ce2041fa3bc07ea7db789f': {
        'appendix': 'http://cloud.cropwatch.com.cn/web/report/detail?id=323&sectionId=7888',
        'unit_source': 'http://cloud.cropwatch.com.cn/web/report/detail?id=323&sectionId=7863',
        'rows': {
            'China': {'corn': (263.45, 268.75, 2.0), 'rice': (211.33, 209.71, -0.8),
                      'wheat': (139.32, 140.94, 1.2), 'soybean': (19.15, 20.23, 5.6)},
            'Cambodia': {'rice': (10.38, 10.09, -2.9)},
            'Indonesia': {'corn': (18.14, 20.62, 13.7), 'rice': (67.94, 68.11, 0.2)},
            'Mongolia': {'wheat': (0.33, 0.33, -1.1)},
            'Myanmar': {'rice': (22.01, 21.00, -4.6)},
            'Philippines': {'corn': (7.11, 7.07, -0.6), 'rice': (20.94, 20.95, 0.0)},
            'Thailand': {'corn': (3.44, 3.52, 2.6), 'rice': (37.41, 39.18, 4.7)},
            'Vietnam': {'corn': (4.04, 4.13, 2.2), 'rice': (47.82, 47.26, -1.2)},
            'Laos': {'rice': (3.82, 4.01, 4.9)},
            'Bangladesh': {'corn': (3.59, 3.23, -10.1), 'rice': (46.57, 46.85, 0.6)},
            'India': {'corn': (43.73, 45.66, 4.4), 'rice': (256.94, 265.02, 3.1),
                      'wheat': (118.16, 116.85, -6.1), 'soybean': (13.77, 13.89, 0.8)},
            'Pakistan': {'corn': (6.39, 6.78, 6.0), 'rice': (13.47, 13.89, 3.1),
                         'wheat': (24.84, 25.10, 1.1)},
            'Sri Lanka': {'rice': (2.39, 2.47, 3.3)},
        },
    },
}

QUARANTINED = {
    '575e9a4804d2073ee2da117e665ef4609606e06d501cb3e8cfb5067b1061f06d': [
        {'country': country, 'crop': 'rice', 'reason':
         'April 2026 country chapter describes dry-season rice; appendix omits season. '
         'Excluded from annual production until the table scope is clarified.'}
        for country in ('Indonesia', 'Thailand', 'Vietnam')
    ],
    '5044c629fc299e314203ab7ebce28caf730ec8ea337aefe40585918f3949f555': [
        {'country': 'China', 'crop': 'wheat', 'reason':
         'June 2026 China tables 2.1/2.2 have apparently interchanged summer-crop/wheat '
         'captions and quantities. Excluded; use the separately published national appendix.'}
    ],
}


def _text(value):
    return ' '.join(str(value).split())


def _year(value):
    match = re.search(r'\b(20\d{2})', _text(value))
    return int(match[1]) if match else None


def _crop(label):
    label = _text(label).lower()
    if 'rice' in label:
        basis = ('paddy_semi_late' if 'semi-late' in label or 'semi late' in label else
                 'paddy_early' if 'early rice' in label else 'paddy')
        return 'rice', basis
    if 'wheat' in label:
        return 'wheat', 'winter_wheat' if 'winter wheat' in label else BASIS['wheat']
    if 'soybean' in label:
        return 'soybean', BASIS['soybean']
    if 'maize' in label or 'corn' in label:
        return 'corn', BASIS['corn']
    return None, None


def _scale(label, metric='production'):
    label = _text(label).lower()
    if metric == 'yield':
        return 0.001 if 'kg/ha' in label else None
    if metric == 'area':
        return 0.001 if '1,000 ha' in label or 'kha' in label else None
    if '10,000 ton' in label or '\u4e07\u5428' in label:
        return 0.01
    if 'million ton' in label:
        return 1
    if 'thousand ton' in label:
        return 0.001
    return None


def _place(place, provincial):
    place = _text(place)
    lowered = place.lower()
    if lowered in ('nan', '', 'country', 'countries', 'province', 'provinces', 'area'):
        return None
    if any(word in lowered for word in ('subtotal', 'sub-total', 'sub total', 'other', 'producer', 'monitor', 'export', 'import')):
        return None
    if provincial:
        national = lowered in ('china total', 'china toal', 'total', 'china', 'national') or lowered.startswith('national total')
        return 'China', '' if national else place
    if 'total' in lowered:
        return None
    return {'World': 'Global', 'USA': 'United States'}.get(place, place), ''


def _unique(rows):
    unique = {}
    for row in rows:
        key = tuple(row[k] for k in ('crop', 'country', 'region', 'target_year', 'commodity_basis', 'metric'))
        if key in unique and unique[key]['value'] != row['value']:
            raise ValueError('Conflicting CropWatch tables for ' + str(key))
        unique[key] = row
    return list(unique.values())


def _html_rows(doc, report_year, include_previous):
    out, source_yoy = [], []
    quarantine = QUARANTINED.get(doc.get('sha256'), [])
    soup = BeautifulSoup(content(doc), 'html.parser')
    for html in soup.select('table'):
        df = pd.read_html(io.StringIO(str(html)), header=None)[0]
        if df.empty:
            continue
        caption = ''
        for previous in html.find_all_previous(['p', 'h3', 'h4'], limit=8):
            text = _text(previous.get_text(' ', strip=True))
            if text.lower().startswith('table'):
                caption = text.lower()
                break
        if isinstance(df.columns, pd.MultiIndex):
            headers = [tuple(map(_text, col)) for col in df.columns]
            data = df
        else:
            depth = 1 if len(df.columns) == 5 else 2
            if len(df) < depth:
                continue
            headers = [tuple(_text(df.iloc[j, i]) for j in range(depth)) for i in range(len(df.columns))]
            data = df.iloc[depth:]
        first = headers[0][0].lower()
        provincial = any('province' in part.lower() for part in headers[0])
        columns = []
        # Quantity column, crop, basis, metric, and the published YoY column.
        if len(headers) == 9 and (provincial or first in ('country', 'countries')):
            for col in (1, 3, 5, 7):
                crop, basis = _crop(headers[col][0])
                if crop:
                    columns.append((col, crop, basis, 'production', col + 1))
        elif len(headers) == 13 and all(word in ' '.join(' '.join(h).lower() for h in headers) for word in ('maize', 'wheat', 'soybean')):
            for crop, start in [('corn', 1), ('rice', 4), ('wheat', 7), ('soybean', 10)]:
                for col in ([start, start + 1] if include_previous else [start + 1]):
                    columns.append((col, crop, 'paddy' if crop == 'rice' else BASIS[crop], 'production', start + 2 if col == start + 1 else None))
        elif len(headers) in (5, 7, 8, 10):
            crop, basis = _crop(caption)
            if not crop:
                continue
            provincial = True
            if len(headers) == 8:
                columns = [(5, crop, basis, 'production', 7), (1, crop, basis, 'area', None), (3, crop, basis, 'yield', None)]
            elif len(headers) == 10:
                for metric, old, new in [('production', 7, 8), ('area', 1, 2), ('yield', 4, 5)]:
                    for col in ([old, new] if include_previous else [new]):
                        columns.append((col, crop, basis, metric, new + 1 if metric == 'production' and col == new else None))
            else:
                old, new, change = (1, 2, 4) if len(headers) == 5 else (1, 4, 6)
                for col in ([old, new] if include_previous else [new]):
                    columns.append((col, crop, basis, 'production', change if col == new else None))
        for col, crop, basis, metric, change_col in columns:
            header = ' '.join(headers[col])
            year = _year(header)
            scale = _scale(header + ' ' + caption, metric)
            if year is None or scale is None:
                continue
            unit = {'production': 'Mt', 'area': 'Mha', 'yield': 't/ha'}[metric]
            method = ('CropWatch provisional monitoring/forecast; ' + caption + '; source column: ' + header +
                      '; explicit table year and unit; rice seasons/winter wheat kept separate; '
                      'source tables can differ from narrative and are not summed across bases.')
            for _, row in data.iterrows():
                location = _place(row.iloc[0], provincial)
                if location is None:
                    continue
                country, region = location
                if any(q['country'] == country and q['crop'] == crop for q in quarantine):
                    continue
                value = pd.to_numeric(row.iloc[col], errors='coerce')
                if pd.isna(value):
                    continue
                result = observation(doc, crop, country, year, float(value) * scale, metric=metric, unit=unit,
                                     basis=basis, year_basis='calendar_year', region=region, methodology=method)
                out.append(result)
                if change_col is not None:
                    change = pd.to_numeric(row.iloc[change_col], errors='coerce')
                    if pd.notna(change):
                        source_yoy.append({**result, 'metric': 'production_yoy', 'value': float(change), 'unit': '%',
                                           'methodology': method + '; published YoY, not inferred from rounded quantities'})
    return _unique(out), _unique(source_yoy)


def tables(doc, report_year, include_previous=False):
    """Keep the historical tables API; optional old-year columns are never inferred."""
    return _html_rows(doc, report_year, include_previous)[0]


def parse_batch(doc, report_year):
    """Return database-compatible forecast/estimate rows plus separate source evidence."""
    if doc['raw_path'].lower().endswith(('.png', '.jpg', '.jpeg')):
        sha = hashlib.sha256(content(doc)).hexdigest()
        if sha != doc.get('sha256'):
            raise ValueError('CropWatch image SHA256 differs from archive metadata')
        table = IMAGE_TABLES.get(sha)
        if table is None:
            raise ValueError('CropWatch image hash needs a reviewed transcription: ' + sha)
        if report_year != 2026:
            raise ValueError('Reviewed CropWatch image table explicitly targets 2026')
        rows, source_yoy = [], []
        for country, crops in table['rows'].items():
            for crop, (old, new, change) in crops.items():
                method = ('CropWatch provisional monitoring/forecast; manually verified Appendix A.1 image; '
                          'published 2025 quantity is a retrospective estimate, not official actual; '
                          'published 2026 quantity is forecast; Mt scale cross-checked with the same issue '
                          'global table ' + table['unit_source'] + '; rice follows source paddy basis; '
                          'image legend: high resolution-based estimates, remote sensing index-based '
                          'estimates, or trend forecast; no official actuals; '
                          'country table labels retained; do not sum with seasonal China tables; '
                          'SHA256=' + sha + '; appendix=' + table['appendix'])
                for year, value in ((2025, old), (2026, new)):
                    rows.append(observation(doc, crop, country, year, value,
                                            basis='paddy' if crop == 'rice' else BASIS[crop],
                                            year_basis='calendar_year', methodology=method))
                source_yoy.append({**rows[-1], 'metric': 'production_yoy', 'value': change, 'unit': '%',
                                   'methodology': method + '; published YoY, not recomputed from rounded amounts'})
    else:
        rows, source_yoy = _html_rows(doc, report_year, include_previous=True)
    notes = []
    if doc.get('sha256') in IMAGE_TABLES:
        notes.append('Only manually checked Asian country rows are transcribed; blank cells are absent, not zero.')
    if doc.get('sha256') == '50c19a95f24f8a6e0ecf2bfc7e83e0d154feb28e4cc40cbd161f7ff161331121':
        notes.append('August Appendix image Global rice 864.69 Mt / wheat 848.88 Mt conflicts with '
                     'section 7944 HTML rice 795.78 Mt / wheat 850.12 Mt. Image Global rows are excluded; '
                     'no replacement, summation, or consensus is applied. Some published YoY cells also '
                     'differ from the ratio of the published quantities; source_yoy retains the printed sign/value.')
    return {'forecast': [r for r in rows if r['target_year'] >= report_year],
            'estimate': [r for r in rows if r['target_year'] < report_year],
            'source_yoy': source_yoy, 'coverage_notes': notes,
            'quarantined': [{**q, 'document_id': doc['document_id'], 'source_url': doc['source_url']}
                            for q in QUARANTINED.get(doc.get('sha256'), [])]}


def discover_sections(doc):
    soup = BeautifulSoup(content(doc), 'html.parser')
    labels = ('global production', 'global crop production', '2.6 china', '4.1 crop', 'production outlook')
    sections = {urljoin(doc['source_url'], a['href']) for a in soup.select('a[href]')
                if any(label in _text(a.get_text(' ', strip=True)).lower() for label in labels)}
    return sorted(sections or {doc['source_url']})


def table_images(doc):
    soup = BeautifulSoup(content(doc), 'html.parser')
    urls = []
    for body in soup.select('div.content'):
        text = _text(body.get_text(' ', strip=True)).lower()
        if body.select('table') or not re.search(r'table\s+a\.1.*production.*cereals.*soybean', text):
            continue
        urls.extend(urljoin(doc['source_url'], img['src']) for img in body.select('img[src]')
                    if '/profile/avatar/' in img['src'])
    return list(dict.fromkeys(urls))


def ingest_report(con, report_doc, report_year):
    """Ingest a known official report into the supplied connection; no implicit DB open."""
    count, issues = 0, []
    metadata = dict(title=report_doc['title'], date_basis=report_doc['publication_date_basis'],
                    available_date=str(report_doc['available_date'])[:10])
    for section in discover_sections(report_doc):
        try:
            doc = download(con, 'cropwatch', section, suffix='.html', **metadata)
            documents = [doc]
            for image_url in table_images(doc):
                documents.append(download(con, 'cropwatch', image_url, suffix='.png', **metadata))
            for source_doc in documents:
                batch = parse_batch(source_doc, report_year)
                inserted = 0
                for status in ('forecast', 'estimate'):
                    insert_rows(con, batch[status], status)
                    inserted += len(batch[status])
                if inserted or batch['quarantined']:
                    save_parsed(source_doc, batch)
                count += inserted
                if inserted:
                    print('CropWatch', report_doc['title'], inserted, source_doc['source_url'])
                issues.extend(q['reason'] for q in batch['quarantined'])
        except Exception as exc:
            issues.append(section + ': ' + str(exc))
            print(issues[-1])
    return {'rows': count, 'issues': list(dict.fromkeys(issues))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reports', type=int, default=8)
    args = ap.parse_args()
    con = connect()
    count, issues, latest = 0, [], None
    try:
        listing = download(con, 'cropwatch', 'http://cloud.cropwatch.com.cn/web/report', suffix='.html')
        soup = BeautifulSoup(content(listing), 'html.parser')
        reports = {}
        for a in soup.select('a[href]'):
            title = _text(a.get_text(' ', strip=True))
            match = re.search(r'(\w+) (20\d{2}) CropWatch Bulletin', title)
            if not match or not re.search(r'detail\?id=\d+$', a['href']):
                continue
            month = datetime.strptime(match[1], '%B').month
            year = int(match[2])
            available = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
            if available <= date.today().isoformat():
                reports[urljoin(listing['source_url'], a['href'])] = (title, year, available)
        for url, (title, year, available) in sorted(reports.items(), key=lambda item: item[1][2], reverse=True)[:args.reports]:
            try:
                doc = download(con, 'cropwatch', url, suffix='.html', title=title,
                               date_basis='Issue month only; availability conservatively month-end', available_date=available)
                result = ingest_report(con, doc, year)
                count += result['rows']
                issues.extend(result['issues'])
                if result['rows']:
                    latest = max(latest or '', available)
            except Exception as exc:
                issues.append(title + ': ' + str(exc))
                print(issues[-1])
        if not count:
            raise ValueError('Reports archived but no supported production tables parsed')
        mark_source(con, 'cropwatch', True, observation_date=latest, rows=count, status='partial',
                    error='Issue-month availability; image coverage limited to reviewed Asian rows; '
                          'table/narrative differences retained. ' + '; '.join(dict.fromkeys(issues)))
    except Exception as exc:
        failed(con, 'cropwatch', exc)
        return 2
    finally:
        con.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
