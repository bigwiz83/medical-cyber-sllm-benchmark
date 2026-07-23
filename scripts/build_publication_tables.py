from __future__ import annotations

import argparse
import csv
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results" / "article_comparisons.csv"
TARGET = ROOT / "tables" / "table3_comparisons.csv"
NUMERIC_COLUMNS = ("effect", "ci_lower", "ci_upper")
P_VALUE_COLUMNS = ("raw_p", "adjusted_p")


def _decimal_places(value: str, places: int = 6) -> str:
    if value == "":
        return ""
    rendered = f"{float(value):.{places}f}".rstrip("0").rstrip(".")
    return "0" if rendered == "-0" else rendered


def _significant_digits(value: str, digits: int = 6) -> str:
    if value == "":
        return ""
    return f"{float(value):.{digits}g}"


def build_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["comparison"] = row["comparison"].replace(" versus ", " − ")
        for column in NUMERIC_COLUMNS:
            row[column] = _decimal_places(row[column])
        for column in P_VALUE_COLUMNS:
            row[column] = _significant_digits(row[column])
    return rows


def render(path: Path) -> None:
    rows = build_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the rounded article comparison table")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as temporary:
            observed = Path(temporary) / TARGET.name
            render(observed)
            if observed.read_bytes() != TARGET.read_bytes():
                print("FAIL: publication comparison table differs from deterministic rounding")
                return 1
        print("PASS: publication comparison table matches deterministic rounding")
        return 0
    render(TARGET)
    print(f"WROTE: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
