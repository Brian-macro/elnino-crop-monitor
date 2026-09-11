"""Fetch and archive the currently enabled local forecast adapters.

Adapters are isolated: one provider may be stale without blocking the others.
"""
import argparse, importlib
from db import connect, insert_rows, mark_source
from archive import download, save_parsed, failed

ADAPTERS = {
    "aafc": "local_sources.aafc",
    "abares": "local_sources.abares",
    "conab": "local_sources.conab",
    "dafw": "local_sources.dafw",
    "cec": "local_sources.cec",
    "ec": "local_sources.ec",
    "bcr": "local_sources.bcr",
    "uga": "local_sources.uga",
}


def replace_parsed_document(con, doc, batch):
    """Keep one current interpretation; raw files and vintage parses are retained."""
    tables = {'forecast':'forecast_production','estimate':'estimated_production','actual':'actual_production'}
    if not isinstance(batch, dict) or not any(batch.get(s) for s in tables):
        raise ValueError('Local source returned no production observations')
    if any(r['document_id'] != doc['document_id'] for s in tables for r in batch.get(s, [])):
        raise ValueError('Parsed document identity mismatch')
    count = 0
    con.execute('BEGIN')
    try:
        for status, table in tables.items():
            con.execute(f'DELETE FROM {table} WHERE document_id=?', [doc['document_id']])
            rows = batch.get(status, [])
            if rows:
                insert_rows(con, rows, status)
                count += len(rows)
        con.execute('COMMIT')
    except Exception:
        con.execute('ROLLBACK')
        raise
    return count


def run(source=None):
    con = connect()
    names = [source] if source else list(ADAPTERS)
    errors = []
    try:
        for name in names:
            module = importlib.import_module(ADAPTERS[name])
            count = 0
            try:
                for item in module.discover():
                    doc = download(con, name, item["url"], suffix=item.get("suffix", ".html"),
                                   date_resolver=getattr(module, "resolve_date", None),
                                   publication_date=item.get("publication_date"),
                                   available_date=item.get("available_date"),
                                   date_basis=item.get("date_basis", "official publication date"),
                                   title=item.get("title", ""))
                    batch = module.parse(doc)
                    count += replace_parsed_document(con, doc, batch)
                    save_parsed(doc, batch)
                mark_source(con, name, True, rows=count, status="ok" if count else "partial")
                print(name, count)
            except Exception as exc:
                failed(con, name, exc); errors.append(f"{name}: {exc}")
        return errors
    finally:
        con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--source", choices=sorted(ADAPTERS)); args = ap.parse_args()
    raise SystemExit(1 if run(args.source) else 0)
