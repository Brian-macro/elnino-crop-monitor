"""Explicit contract mapping, separate from crop-output definitions."""

import json
from pathlib import Path

CONTRACTS = json.loads(
    (Path(__file__).resolve().parents[1] / "config/futures_contracts.json").read_text(
        encoding="utf-8"
    )
)
