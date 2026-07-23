from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.mixed_effects import (  # noqa: E402
    MixedEffectsAnalysisReport,
    analyze_mixed_effects,
)

FROZEN_REPORT_TOLERANCE = 1e-12
REFIT_TOLERANCE = 2e-3


@dataclass(frozen=True, slots=True)
class Comparison:
    identifier: str
    comparator: str
    intervention: str


COMPARISONS = (
    Comparison("qwen_fixed_vs_single", "qwen_single_rag", "qwen_fixed_team"),
    Comparison(
        "qwen_autonomous_vs_fixed", "qwen_fixed_team", "qwen_autonomous_team"
    ),
    Comparison(
        "qwen_autonomous_vs_single", "qwen_single_rag", "qwen_autonomous_team"
    ),
)


def _positive_outcome(report: MixedEffectsAnalysisReport) -> Any:
    return next(item for item in report.outcomes if item.outcome == "verified_detection")


def _values(report: MixedEffectsAnalysisReport) -> tuple[float, ...]:
    outcome = _positive_outcome(report)
    effect = outcome.condition_effect
    marginal = outcome.marginal_probability
    if effect is None or marginal is None:
        raise ValueError("verified-detection model lacks a condition effect or marginal contrast")
    return (
        effect.transformed_estimate,
        effect.ci_lower,
        effect.ci_upper,
        effect.two_sided_p_value,
        marginal.absolute_probability_difference,
        marginal.ci_lower,
        marginal.ci_upper,
    )


def _article_rows() -> list[tuple[float, ...]]:
    path = ROOT / "supplement" / "table_s2_model_sensitivity.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = (
        "conditional_estimate",
        "conditional_ci_lower",
        "conditional_ci_upper",
        "conditional_p",
        "standardized_probability_difference",
        "standardized_ci_lower",
        "standardized_ci_upper",
    )
    return [tuple(float(row[field]) for field in fields) for row in rows]


def _same(left: tuple[float, ...], right: tuple[float, ...], *, tolerance: float) -> bool:
    return all(
        math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)
        for a, b in zip(left, right, strict=True)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path)
    args = parser.parse_args()

    article = _article_rows()
    errors: list[str] = []
    reports: dict[str, MixedEffectsAnalysisReport] = {}
    for comparison, article_values in zip(COMPARISONS, article, strict=True):
        directory = ROOT / "data" / "mixed_effects" / comparison.identifier
        expected = MixedEffectsAnalysisReport.model_validate_json(
            (directory / "expected_report.json").read_text(encoding="utf-8")
        )
        if not _same(
            _values(expected), article_values, tolerance=FROZEN_REPORT_TOLERANCE
        ):
            errors.append(f"{comparison.identifier}: expected report differs from article table")
        observed = analyze_mixed_effects(
            scoring_output_directory=directory,
            dependency_lock=ROOT / "environment" / "original-analysis.uv.lock",
            comparator=comparison.comparator,
            intervention=comparison.intervention,
        )
        reports[comparison.identifier] = observed
        if not _same(_values(observed), article_values, tolerance=REFIT_TOLERANCE):
            errors.append(
                f"{comparison.identifier}: refit differs by more than "
                f"{REFIT_TOLERANCE:g}"
            )
        outcome = _positive_outcome(observed)
        if outcome.status != "MIXED_MODEL" or "BFGS" not in outcome.selected_estimator:
            errors.append(
                f"{comparison.identifier}: prespecified first-line model was not selected"
            )

    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    if args.output is not None:
        args.output.mkdir(parents=True, exist_ok=True)
        for identifier, report in reports.items():
            (args.output / f"{identifier}.json").write_text(
                json.dumps(report.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
                + "\n",
                encoding="utf-8",
            )
    print(
        json.dumps(
            {
                "status": "PASS",
                "comparisons": len(COMPARISONS),
                "frozen_report_tolerance": FROZEN_REPORT_TOLERANCE,
                "refit_tolerance": REFIT_TOLERANCE,
                "output": None if args.output is None else str(args.output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
