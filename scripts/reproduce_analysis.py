from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.analysis import analyze, write_outputs  # noqa: E402


def _coerce(value: str) -> Any:
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {key: _coerce(value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _equal(expected: Any, observed: Any, *, tolerance: float = 1e-12) -> bool:
    if expected is None or observed is None:
        return expected is observed
    if isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
        return math.isclose(float(expected), float(observed), rel_tol=0.0, abs_tol=tolerance)
    return expected == observed


def _compare_csv(expected_path: Path, observed_path: Path) -> list[str]:
    expected = _read_csv(expected_path)
    observed = _read_csv(observed_path)
    errors: list[str] = []
    if len(expected) != len(observed):
        return [f"row count differs for {expected_path.name}: {len(expected)} != {len(observed)}"]
    for index, (left, right) in enumerate(zip(expected, observed, strict=True), start=1):
        if tuple(left) != tuple(right):
            errors.append(f"headers differ for {expected_path.name}")
            break
        for key in left:
            if not _equal(left[key], right[key]):
                errors.append(
                    f"{expected_path.name} row {index} field {key}: {left[key]!r} != {right[key]!r}"
                )
    return errors


def check(result: dict[str, Any]) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp)
        write_outputs(output, result)
        errors: list[str] = []
        for name in (
            "condition_summary.csv",
            "subgroup_results.csv",
            "retrieval_window_recall.csv",
            "article_comparisons.csv",
        ):
            errors.extend(_compare_csv(ROOT / "results" / name, output / name))
        expected_json = json.loads(
            (ROOT / "results" / "statistical_results.json").read_text(encoding="utf-8")
        )
        observed_json = json.loads(
            (output / "statistical_results.json").read_text(encoding="utf-8")
        )
        if expected_json != observed_json:
            errors.append("statistical_results.json differs from deterministic reconstruction")
        return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce benchmark summaries and paired inference"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="compare with locked result files")
    group.add_argument("--output", type=Path, help="write derived files to this directory")
    args = parser.parse_args()
    result = analyze(ROOT / "data" / "derived" / "integrated_cell_scores.csv")
    if args.check:
        errors = check(result)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: deterministic analysis matches all locked result files")
        return 0
    assert args.output is not None
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.resolve().relative_to(ROOT.resolve())
    write_outputs(output, result)
    print(f"WROTE: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
