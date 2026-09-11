import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_local_pair_replaces_both_years():
    from composite import pair_components

    out = pair_components(
        {2025: {"China": 300.0, "Other": 700.0}, 2026: {"China": 310.0, "Other": 720.0}},
        {2025: {"China": 303.0}, 2026: {"China": 306.0}},
        2026,
    )
    assert out["current"] == 1026.0
    assert out["previous"] == 1003.0
    assert out["yoy"] == pytest.approx((1026 / 1003 - 1) * 100)
    assert out["components"]["China"]["source"] == "local"


def test_missing_local_prior_keeps_national_current_and_suppresses_yoy():
    from composite import pair_components

    out = pair_components({2025: {"China": 300.0}, 2026: {"China": 310.0}}, {2026: {"China": 306.0}}, 2026)
    assert out["current"] == 306.0 and out["previous"] is None
    assert out['yoy'] is None
    assert out["components"]["China"]["comparison_reason"] == "missing_local_prior"


def test_ineligible_local_source_falls_back():
    from composite import pair_components

    out = pair_components(
        {2025: {"China": 300.0}, 2026: {"China": 310.0}},
        {2025: {"China": 303.0}, 2026: {"China": 306.0}},
        2026,
        eligible={"China": False},
    )
    assert out["current"] == 310.0
    assert not out["components"]["China"]["replaced"]
