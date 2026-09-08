import sys, json
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_jsonp_is_data_not_executable_and_missing_volume_is_explicit():
    from fetch_futures import parse_payload
    from futures_config import CONTRACTS

    text = '/*<script>location.href="bad";</script>*/ var example=([{"date":"2020-01-02","open":"100","high":"110","low":"90","close":"105","volume":"0"}]);'
    rows = parse_payload(text.encode(), CONTRACTS["us_corn"], today="2020-01-04")
    assert len(rows) == 1 and rows[0]["close"] == 105 and rows[0]["volume"] is None


def test_incomplete_today_and_untraded_quotes_not_used():
    from fetch_futures import parse_payload
    from futures_config import CONTRACTS

    values = [
        dict(d="2020-01-02", o="10", h="12", l="9", c="11", v="0", p="0", s="0"),
        dict(d="2020-01-03", o="10", h="12", l="9", c="11", v="8", p="9", s="11"),
    ]
    rows = parse_payload(
        ("x=(" + json.dumps(values) + ");").encode(),
        CONTRACTS["cn_corn"],
        today="2020-01-03",
    )
    assert len(rows) == 1 and not rows[0]["usable"]


def test_event_index_uses_common_observed_month_and_no_gap_fill():
    from event_study import price_window

    a = {"2023-01": 10, "2023-03": 20}
    b = {"2023-01": 20, "2023-02": 30, "2023-03": 40}
    r = price_window(a, b, ["2023-01", "2023-02", "2023-03"])
    assert r["base_month"] == "2023-01"
    assert r["domestic_index"] == [100, None, 200]
    assert r["overseas_index"] == [100, 150, 200]
    assert r["domestic_change"] == 100


def test_missing_price_period_and_zero_consumption_remain_missing():
    from event_study import price_window, stocks_to_use

    r = price_window({}, {"2023-01": 12}, ["2023-01", "2023-02"])
    assert r["domestic_index"] == [None, None]
    assert r["domestic_change"] is None
    assert stocks_to_use(12, 0) is None
    assert stocks_to_use(None, 100) is None
    assert stocks_to_use(12, 100) == 12
