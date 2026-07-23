"""Run the prespecified explanatory mixed-model/GEE sequence on scorer exports."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.mixed_effects import (  # noqa: E402
    analyze_mixed_effects,
    write_report_once,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scoring-output-directory", type=Path, required=True)
    parser.add_argument(
        "--dependency-lock", type=Path, default=ROOT / "requirements-lock.txt"
    )
    parser.add_argument("--comparator", default="qwen_single_rag")
    parser.add_argument("--intervention", default="qwen_fixed_team")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-profile", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = analyze_mixed_effects(
        scoring_output_directory=args.scoring_output_directory,
        dependency_lock=args.dependency_lock,
        comparator=args.comparator,
        intervention=args.intervention,
        require_primary_matrix=not args.fixture_profile,
    )
    if args.execute:
        output = write_report_once(args.output, report)
        payload = {"status": report.status, "output": str(output), "model_calls_made": 0}
    else:
        payload = {
            "status": report.status,
            "mode": "preflight",
            "output_would_be": str(args.output),
            "model_calls_made": 0,
        }
    print(json.dumps(payload, sort_keys=True))
    return 0 if report.status != "FAIL" else 4


if __name__ == "__main__":
    raise SystemExit(main())
