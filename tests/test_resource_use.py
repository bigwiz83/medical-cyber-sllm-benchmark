from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_supplementary_resource_table_matches_frozen_aggregate() -> None:
    result = (ROOT / "results" / "resource_use.csv").read_bytes()
    supplement = (ROOT / "supplement" / "table_s3_resource_use.csv").read_bytes()
    assert result == supplement
