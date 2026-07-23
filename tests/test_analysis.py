from __future__ import annotations

import math
from pathlib import Path

from medcyber_benchmark.analysis import CONDITION_ORDER, analyze, read_cells

ROOT = Path(__file__).resolve().parents[1]
CELL_PATH = ROOT / "data" / "derived" / "integrated_cell_scores.csv"


def test_exact_cell_inventory() -> None:
    rows = read_cells(CELL_PATH)
    assert len(rows) == 3_000
    assert {row["condition_id"] for row in rows} == set(CONDITION_ORDER)
    assert len({row["scenario_id"] for row in rows}) == 60
    assert len({row["family_id"] for row in rows}) == 30


def test_condition_results() -> None:
    result = analyze(CELL_PATH)
    summary = {row["condition_id"]: row for row in result["condition_summary"]}
    assert sum(row["complete"] for row in summary.values()) == 2_759
    assert sum(row["failed"] for row in summary.values()) == 236
    assert sum(row["refused"] for row in summary.values()) == 5
    assert math.isclose(summary["qwen_single_rag"]["mean_run_f1"], 0.6341463414634146)
    assert math.isclose(summary["qwen_autonomous_team"]["mean_run_f1"], 0.6153846153846154)
    assert math.isclose(summary["qwen_fixed_team"]["mean_run_f1"], 0.6046511627906976)
    assert summary["qwen_without_retrieval"]["precision"] is None
    assert summary["qwen_without_retrieval"]["mean_run_f1"] == 0.0
    assert math.isclose(summary["gpt_oss_single_rag"]["mean_run_f1"], 0.09219638242894057)
    assert math.isclose(summary["gpt_oss_single_rag"]["pooled_count_f1"], 0.09216589861751152)


def test_paired_inference() -> None:
    result = analyze(CELL_PATH)
    comparisons = {
        row["comparison_id"]: row
        for row in result["statistical_results"]["comparisons"]
    }
    primary = comparisons["qwen_fixed_vs_single"]
    assert math.isclose(primary["effect"], -0.029495178672717004, abs_tol=1e-15)
    assert math.isclose(primary["ci_lower"], -0.13167013167013164, abs_tol=1e-15)
    assert math.isclose(primary["ci_upper"], 0.06666666666666665, abs_tol=1e-15)
    assert math.isclose(primary["raw_p"], 0.5831416858314169, abs_tol=1e-15)

    retrieval = comparisons["retrieval_retained_vs_removed"]
    assert retrieval["effect"] == 0.75
    assert retrieval["ci_lower"] == 0.5
    assert math.isclose(retrieval["ci_upper"], 0.9166666666666666, abs_tol=1e-15)
    assert math.isclose(retrieval["adjusted_p"], 0.00019998000199980003, abs_tol=1e-15)

    autonomous = comparisons["qwen_autonomous_vs_fixed"]
    assert math.isclose(autonomous["effect"], 0.01073345259391778, abs_tol=1e-15)
    assert math.isclose(autonomous["ci_lower"], -0.11986062717770041, abs_tol=1e-15)
    assert math.isclose(autonomous["ci_upper"], 0.14377406931964054, abs_tol=1e-15)
    assert math.isclose(autonomous["raw_p"], 0.8801119888011198, abs_tol=1e-15)

