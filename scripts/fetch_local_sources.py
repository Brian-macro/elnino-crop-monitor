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
                                   publication_date=item.get("publication_date"),
                                   available_date=item.get("available_date"),
                                   date_basis=item.get("date_basis", "official publication date"),
                                   title=item.get("title", ""))
                    batch = module.parse(doc)
                    for status in ("forecast", "estimate", "actual"):
                        rows = batch.get(status, []) if isinstance(batch, dict) else []
                        if rows:
                            insert_rows(con, rows, status); count += len(rows)
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
