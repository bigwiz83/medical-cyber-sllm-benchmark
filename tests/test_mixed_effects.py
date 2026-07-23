from __future__ import annotations

import csv
import math
from pathlib import Path

from medcyber_benchmark.mixed_effects import MixedEffectsAnalysisReport

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIERS = (
    "qwen_fixed_vs_single",
    "qwen_autonomous_vs_fixed",
    "qwen_autonomous_vs_single",
)


def test_locked_mixed_effects_reports_match_supplement() -> None:
    with (ROOT / "supplement" / "table_s2_model_sensitivity.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(IDENTIFIERS)
    for identifier, row in zip(IDENTIFIERS, rows, strict=True):
        path = ROOT / "data" / "mixed_effects" / identifier / "expected_report.json"
        report = MixedEffectsAnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
        outcome = next(item for item in report.outcomes if item.outcome == "verified_detection")
        assert outcome.condition_effect is not None
        assert outcome.marginal_probability is not None
        assert math.isclose(
            outcome.condition_effect.transformed_estimate,
            float(row["conditional_estimate"]),
            abs_tol=1e-12,
        )
        assert math.isclose(
            outcome.marginal_probability.absolute_probability_difference,
            float(row["standardized_probability_difference"]),
            abs_tol=1e-12,
        )
