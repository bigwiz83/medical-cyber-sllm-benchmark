from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "derived" / "integrated_cell_scores.csv"
TARGET = ROOT / "configs" / "evaluation_matrix.jsonl"


def main() -> int:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(
        key=lambda row: (
            row["condition_id"],
            int(row["run_index"]),
            row["blind_case_id"],
        )
    )
    records = []
    for ordinal, row in enumerate(rows):
        records.append(
            {
                "matrix_ordinal": ordinal,
                "condition_id": row["condition_id"],
                "blind_case_id": row["blind_case_id"],
                "scenario_id": row["scenario_id"],
                "family_id": row["family_id"],
                "stratum": row["stratum"],
                "run_index": int(row["run_index"]),
                "scheduled_model_calls": 5,
            }
        )
    if len(records) != 3_000:
        raise SystemExit(f"expected 3,000 matrix records, found {len(records)}")
    keys = {
        (item["condition_id"], item["blind_case_id"], item["run_index"])
        for item in records
    }
    if len(keys) != 3_000:
        raise SystemExit("evaluation matrix keys are not unique")
    TARGET.write_text(
        "".join(
            json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
            for item in records
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records to {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
