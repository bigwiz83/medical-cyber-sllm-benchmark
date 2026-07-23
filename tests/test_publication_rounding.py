from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_machine_result_retains_full_precision() -> None:
    statistics = json.loads(
        (ROOT / "results" / "statistical_results.json").read_text(encoding="utf-8")
    )
    canonical = {
        item["comparison_id"]: item for item in statistics["comparisons"]
    }
    source = {
        row["comparison"]: row for row in _rows(ROOT / "results" / "article_comparisons.csv")
    }
    item = canonical["gpt_oss_fixed_vs_single"]
    assert math.isclose(float(source[item["comparison"]]["raw_p"]), item["raw_p"], abs_tol=0.0)
    assert len(source[item["comparison"]]["raw_p"]) > len(f"{item['raw_p']:.6g}")


def test_article_table_is_explicitly_rounded() -> None:
    source = _rows(ROOT / "results" / "article_comparisons.csv")
    article = _rows(ROOT / "tables" / "table3_comparisons.csv")
    assert len(source) == len(article)
    for raw, displayed in zip(source, article, strict=True):
        assert displayed["effect"] == f"{float(raw['effect']):.6f}".rstrip("0").rstrip(".")
        for column in ("raw_p", "adjusted_p"):
            expected = "" if raw[column] == "" else f"{float(raw[column]):.6g}"
            assert displayed[column] == expected


def test_figure_effect_source_round_trips_to_article_table() -> None:
    figure = _rows(ROOT / "figures" / "source_data" / "figure3a_f1_effects.csv")
    article = {
        row["comparison"]: row for row in _rows(ROOT / "tables" / "table3_comparisons.csv")
    }
    assert len(figure) == 10
    for raw in figure:
        displayed = article[raw["comparison"]]
        for column in ("effect", "ci_lower", "ci_upper"):
            expected = f"{float(raw[column]):.6f}".rstrip("0").rstrip(".")
            assert displayed[column] == expected
        for column in ("raw_p", "adjusted_p"):
            expected = "" if raw[column] == "" else f"{float(raw[column]):.6g}"
            assert displayed[column] == expected
