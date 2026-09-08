import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_china_sources_are_crop_specific():
    from policy import local_source
    assert local_source("China", "corn") == "casde"
    assert local_source("China", "soybean") == "casde"
    assert local_source("China", "sugar") == "casde"
    assert local_source("China", "wheat") == "cropwatch"
    assert local_source("China", "rice") is None


def test_unverified_crosswalk_is_not_composite_eligible():
    from policy import composite_rule
    assert not composite_rule("China", "rice")["eligible"]
