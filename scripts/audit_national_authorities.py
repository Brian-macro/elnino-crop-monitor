"""Check declared public entrances; accessibility never implies data integration."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import requests
from config import ROOT


def inspect(row):
    row = dict(row, checked_at=datetime.now(timezone.utc).isoformat())
    if not row.get('url'):
        return row
    try:
        response = requests.get(row['url'], timeout=(10,20))
        row['http_status'] = response.status_code
        row['access_status'] = 'verified' if response.ok else 'blocked'
        row['access_error'] = None if response.ok else 'HTTP ' + str(response.status_code)
    except requests.RequestException as error:
        row['access_status'] = 'blocked'
        row['access_error'] = str(error)[:300]
    return row


if __name__ == '__main__':
    path = ROOT/'config'/'national_authorities.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=6) as pool:
        data['countries'] = list(pool.map(inspect,data['countries']))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in data['countries']:
        print(row['country'], row.get('access_status'))
