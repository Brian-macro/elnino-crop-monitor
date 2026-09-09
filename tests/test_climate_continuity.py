"""Calendar-month semantics for archived climate summary statistics."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research import climate_bundle


def summary(months, values, index="ONI"):
    frame = pd.DataFrame({"index_name": index, "date": pd.to_datetime(months), "value": values})
    connection = SimpleNamespace(execute=lambda sql: SimpleNamespace(fetchdf=lambda: frame))
    return climate_bundle(connection)["current"][index]


@pytest.mark.parametrize("index", ["ONI", "Nino3.4"])
def test_missing_previous_month_breaks_warm_run_and_change(index):
    result = summary(["2000-10-01", "2000-11-01", "2001-01-01"], [0.5, 0.7, 1.2], index)
    assert result["warm_seasons"] == 1
    assert result["chg_1m"] is None
    assert result["chg_3m"] == pytest.approx(0.7)


def test_three_month_change_uses_calendar_month_not_fourth_last_row():
    result = summary(["2000-08-01", "2000-09-01", "2000-11-01", "2000-12-01"], [0.5, 0.7, 1.0, 1.2])
    assert result["chg_3m"] == pytest.approx(0.5)
    assert result["chg_1m"] == pytest.approx(0.2)
    assert result["warm_seasons"] == 2


def test_missing_three_month_reference_does_not_substitute_older_value():
    result = summary(["2000-08-01", "2000-10-01", "2000-11-01", "2000-12-01"], [0.5, 0.7, 1.0, 1.2])
    assert result["chg_3m"] is None


def test_contiguous_cross_year_run_preserves_existing_statistics():
    result = summary(["2000-10-01", "2000-11-01", "2000-12-01", "2001-01-01"], [0.5, 0.7, 1.0, 1.2])
    assert result["warm_seasons"] == 4
    assert result["chg_1m"] == pytest.approx(0.2)
    assert result["chg_3m"] == pytest.approx(0.7)
    assert result["sample_size"] == 4
    assert result["percentile"] == 100.0


def test_single_cold_observation_has_zero_warm_duration_and_no_changes():
    result = summary(["2001-01-01"], [-0.5])
    assert result["warm_seasons"] == 0
    assert result["chg_1m"] is None
    assert result["chg_3m"] is None
