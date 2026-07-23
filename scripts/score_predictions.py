from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.scoring import (  # noqa: E402
    jsonl_bytes,
    score_predictions,
    write_scores,
)

DEFAULT_PREDICTIONS = ROOT / "data" / "predictions" / "final_predictions.jsonl"
EXPECTED_SCORES = ROOT / "data" / "derived" / "integrated_cell_scores.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score the released structured predictions against the frozen reference."
    )
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Require exact field and byte equality with the released 3,000-cell score matrix.",
    )
    args = parser.parse_args()
    rows = score_predictions(ROOT, args.predictions)
    encoded = jsonl_bytes(rows)
    if args.check:
        expected_rows = _read_jsonl(EXPECTED_SCORES)
        if rows != expected_rows:
            raise SystemExit("rescored rows differ from the released score matrix")
        if encoded != EXPECTED_SCORES.read_bytes():
            raise SystemExit("rescored JSONL bytes differ from the released score matrix")
        print("PASS: 3,000 prediction rows reproduce the released score matrix exactly")
    if args.output is not None:
        write_scores(args.output, rows)
        print(f"wrote {len(rows):,} scored rows to {args.output}")
    if not args.check and args.output is None:
        parser.error("select --check, --output, or both")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
