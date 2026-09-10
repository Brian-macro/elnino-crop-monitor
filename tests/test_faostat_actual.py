import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_faostat_parser_keeps_official_production_and_excludes_estimates():
    from fetch_faostat import parse_actuals

    csv_text = """Area Code,Area Code (M49),Area,Item Code,Item Code (CPC),Item,Element Code,Element,Year Code,Year,Unit,Value,Flag,Note
"351","'001","World","15","'0111","Wheat","5510","Production","2024","2024","t","798481711.070000","A",
"351","'001","World","44","'0114","Maize (corn)","5510","Production","2024","2024","t","1218205573.820000","A",
"351","'001","World","27","'0137","Rice","5510","Production","2024","2024","t","820223277.890000","A",
"351","'001","World","236","'0145","Soya beans","5510","Production","2024","2024","t","397671688.560000","A",
"351","'001","World","156","'0180","Raw cane or beet sugar (centrifugal only)","5510","Production","2023","2023","t","187555273.390000","E",
"41","'156","China","15","'0111","Wheat","5510","Production","2024","2024","t","140105000.000000","A",
"41","'156","China","27","'0137","Rice","5510","Production","2024","2024","t","209173000.000000","A",
"""
    doc = {
        "document_id": "fixture",
        "source": "faostat",
        "source_url": "https://example.org/faostat.zip",
        "publication_date": None,
        "available_date": "2026-09-10",
        "download_timestamp": "2026-09-10T00:00:00Z",
    }

    rows = parse_actuals(csv_text, doc)
    values = {(r["crop"], r["country"]): r for r in rows}

    assert values["wheat", "Global"]["value"] == pytest.approx(798.48171107)
    assert values["corn", "Global"]["value"] == pytest.approx(1218.20557382)
    assert values["rice", "China"]["commodity_basis"] == "paddy"
    assert values["rice", "China"]["year_basis"] == "calendar_year"
    assert "sugar", "Global" not in values
    assert all(r["methodology"].startswith("Official reported actual") for r in rows)
