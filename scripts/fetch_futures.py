"""Archive Sina raw JSONP used by AkShare; prices are never stored in spot tables."""

import argparse
import hashlib
import json
import math
from datetime import date
from urllib.parse import urlencode
import pandas as pd
from archive import download, content, save_parsed, failed
from db import connect, mark_source
from futures_config import CONTRACTS


def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def endpoint(contract):
    if contract["market"] == "china":
        base = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_V21052021_4_12=/InnerFuturesNewService.getDailyKLine"
        return (
            base + "?" + urlencode(dict(symbol=contract["symbol"], type="2021_04_12"))
        )
    # The callback identifier is a transport name, not a publication date.
    base = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_S2026_9_8=/GlobalFuturesService.getGlobalFuturesDailyKLine"
    return base + "?" + urlencode(dict(symbol=contract["symbol"], source="web"))


def parse_payload(payload, contract, today=None):
    cutoff = str(today or date.today())[:10]
    text = payload.decode("utf-8-sig")
    start = text.find("[")
    if start < 0:
        raise ValueError("Sina response has no JSON array")
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(data, list):
        raise ValueError("Expected daily quote list")
    domestic = contract["market"] == "china"
    rows = []
    for raw in data:
        if not isinstance(raw, dict):
            raise ValueError("Daily quote schema changed")
        day = str(raw.get("d" if domestic else "date", ""))[:10]
        try:
            date.fromisoformat(day)
        except ValueError:
            raise ValueError("Unrecognised quote date: " + day)
        if day >= cutoff:
            continue  # Conservatively exclude the current incomplete trading day.
        mapping = (
            {
                "open": "o",
                "high": "h",
                "low": "l",
                "close": "c",
                "volume": "v",
                "open_interest": "p",
                "settlement": "s",
            }
            if domestic
            else {
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "open_interest": "position",
                "settlement": "settlement",
            }
        )
        row = {name: number(raw.get(key)) for name, key in mapping.items()}
        if row["close"] is None or row["close"] <= 0:
            continue
        if row["settlement"] == 0:
            row["settlement"] = None
        if not domestic:
            if row["volume"] == 0:
                row["volume"] = None
            if row["open_interest"] == 0:
                row["open_interest"] = None
        row.update(
            date=day,
            usable=(
                (row["volume"] is not None and row["volume"] > 0) if domestic else True
            ),
        )
        rows.append(row)
    if not rows:
        raise ValueError("No completed historical quotes")
    unique = {row["date"]: row for row in rows}
    return [unique[day] for day in sorted(unique)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", nargs="*", choices=list(CONTRACTS))
    args = ap.parse_args()
    con = connect()
    errors = 0
    try:
        for ident in args.series or CONTRACTS:
            spec = CONTRACTS[ident]
            try:
                doc = download(
                    con,
                    spec["source"],
                    endpoint(spec),
                    suffix=".jsonp",
                    title=spec["label"],
                    date_basis="Source publication timestamp unavailable; first observed archive date",
                )
                parsed = parse_payload(content(doc), spec)
                rows = []
                for row in parsed:
                    rows.append(
                        dict(
                            **row,
                            record_id=hashlib.sha256(
                                (doc["document_id"] + ident + row["date"]).encode()
                            ).hexdigest(),
                            document_id=doc["document_id"],
                            series_id=ident,
                            crop=spec["crop"],
                            market=spec["market"],
                            symbol=spec["symbol"],
                            currency=spec["currency"],
                            unit=spec["unit"],
                            commodity_basis=spec["basis"],
                            source=spec["source"],
                            available_date=str(doc["available_date"])[:10],
                            roll_method=spec["roll_method"]
                        )
                    )
                con.execute("BEGIN")
                try:
                    con.register("_future_rows", pd.DataFrame(rows))
                    con.execute(
                        "INSERT INTO futures_prices BY NAME SELECT * FROM _future_rows ON CONFLICT DO NOTHING"
                    )
                    con.unregister("_future_rows")
                    con.execute("COMMIT")
                except Exception:
                    con.execute("ROLLBACK")
                    raise
                save_parsed(doc, rows)
                last = (
                    max(r["date"] for r in rows if r["usable"])
                    if any(r["usable"] for r in rows)
                    else None
                )
                mark_source(
                    con,
                    spec["source"],
                    True,
                    observation_date=last,
                    rows=len(rows),
                    status="partial",
                    error="Provider continuous contract; underlying month/roll method unavailable. Current-day bars excluded. "
                    + (
                        "Zero-volume domestic quotes retained but excluded from charts."
                        if spec["market"] == "china"
                        else "Zero volume/position fields treated as unavailable; not evidence of no trading."
                    ),
                )
                print(ident, len(rows), "last completed", last, flush=True)
            except Exception as e:
                failed(con, spec["source"], e)
                errors += 1
    finally:
        con.close()
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
