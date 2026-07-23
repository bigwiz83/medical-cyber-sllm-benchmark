from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

RESAMPLES = 10_000
MAIN_SEED = 2_026_071_901
AUTONOMOUS_SEED = 2_026_072_201

CONDITION_ORDER = (
    "qwen_single_rag",
    "qwen_autonomous_team",
    "qwen_fixed_team",
    "qwen_without_evidence_check",
    "qwen_without_context_role",
    "qwen_without_retrieval",
    "gemma_single_rag",
    "gemma_fixed_team",
    "gpt_oss_single_rag",
    "gpt_oss_fixed_team",
)

CONDITION_LABELS = {
    "qwen_single_rag": "Qwen single-RAG",
    "qwen_autonomous_team": "Qwen autonomous team",
    "qwen_fixed_team": "Qwen fixed team",
    "qwen_without_evidence_check": "Qwen without evidence checking",
    "qwen_without_context_role": "Qwen without clinical-context agent",
    "qwen_without_retrieval": "Qwen without retrieval",
    "gemma_single_rag": "Gemma single-RAG",
    "gemma_fixed_team": "Gemma fixed team",
    "gpt_oss_single_rag": "gpt-oss single-RAG",
    "gpt_oss_fixed_team": "gpt-oss fixed team",
}

BACKBONES = {
    "qwen_single_rag": "Qwen 3.5 27B",
    "qwen_autonomous_team": "Qwen 3.5 27B",
    "qwen_fixed_team": "Qwen 3.5 27B",
    "qwen_without_evidence_check": "Qwen 3.5 27B",
    "qwen_without_context_role": "Qwen 3.5 27B",
    "qwen_without_retrieval": "Qwen 3.5 27B",
    "gemma_single_rag": "Gemma 3 27B",
    "gemma_fixed_team": "Gemma 3 27B",
    "gpt_oss_single_rag": "gpt-oss 20B",
    "gpt_oss_fixed_team": "gpt-oss 20B",
}

STRATUM_ORDER = (
    "recent_kev_0_30",
    "recent_kev_31_60",
    "recent_kev_61_90",
    "other_cve",
    "synthetic_misconfiguration",
    "clean_control",
)

STRATUM_LABELS = {
    "recent_kev_0_30": "Recent KEV, 0-30 days",
    "recent_kev_31_60": "Recent KEV, 31-60 days",
    "recent_kev_61_90": "Recent KEV, 61-90 days",
    "other_cve": "Other CVE",
    "synthetic_misconfiguration": "Synthetic misconfiguration",
    "clean_control": "Clean control",
}

EXPECTED_FAMILY_STRATA = {
    "recent_kev_0_30": 4,
    "recent_kev_31_60": 4,
    "recent_kev_61_90": 4,
    "other_cve": 6,
    "synthetic_misconfiguration": 7,
    "clean_control": 5,
}


@dataclass(frozen=True, slots=True)
class Draws:
    family_weights: NDArray[np.int64]
    run_indices: NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class Contrast:
    effect: float
    ci_lower: float
    ci_upper: float
    raw_p: float
    distribution: NDArray[np.float64]


def read_cells(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    **raw,
                    "run_index": int(raw["run_index"]),
                    "positive_reference_count": int(raw["positive_reference_count"]),
                    "tp_ev": int(raw["tp_ev"]),
                    "fp": int(raw["fp"]),
                    "fn": int(raw["fn"]),
                }
            )
    validate_cells(rows)
    return rows


def validate_cells(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 3_000:
        raise ValueError(f"expected 3,000 cells, found {len(rows)}")
    keys = {
        (row["condition_id"], row["scenario_id"], row["run_index"])
        for row in rows
    }
    if len(keys) != 3_000:
        raise ValueError("condition/scenario/repetition keys are not unique")
    if set(row["condition_id"] for row in rows) != set(CONDITION_ORDER):
        raise ValueError("condition inventory differs from the ten public conditions")
    if set(row["run_index"] for row in rows) != {1, 2, 3, 4, 5}:
        raise ValueError("repetition inventory differs from 1 through 5")
    if len({row["scenario_id"] for row in rows}) != 60:
        raise ValueError("scenario inventory differs from 60")
    if len({row["family_id"] for row in rows}) != 30:
        raise ValueError("family inventory differs from 30")
    counts = Counter(row["condition_id"] for row in rows)
    if set(counts.values()) != {300}:
        raise ValueError("every condition must have exactly 300 cells")
    statuses = Counter(row["run_status"] for row in rows)
    if statuses != Counter({"complete": 2_759, "failed": 236, "refusal": 5}):
        raise ValueError(f"terminal status totals differ: {dict(statuses)}")
    family_strata: dict[str, str] = {}
    for row in rows:
        prior = family_strata.setdefault(row["family_id"], row["stratum"])
        if prior != row["stratum"]:
            raise ValueError("one family occurs in multiple strata")
    if Counter(family_strata.values()) != Counter(EXPECTED_FAMILY_STRATA):
        raise ValueError("family allocation differs from the frozen six-stratum design")


def _metric(tp: int, fp: int, fn: int) -> tuple[float | None, float | None, float | None]:
    precision = None if tp + fp == 0 else tp / (tp + fp)
    recall = None if tp + fn == 0 else tp / (tp + fn)
    denominator = 2 * tp + fp + fn
    f1 = None if denominator == 0 else (2 * tp) / denominator
    return precision, recall, f1


def condition_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for condition_id in CONDITION_ORDER:
        selected = [row for row in rows if row["condition_id"] == condition_id]
        statuses = Counter(row["run_status"] for row in selected)
        tp = sum(row["tp_ev"] for row in selected)
        fp = sum(row["fp"] for row in selected)
        fn = sum(row["fn"] for row in selected)
        precision, recall, pooled_f1 = _metric(tp, fp, fn)
        run_f1: list[float] = []
        for run_index in range(1, 6):
            run_rows = [row for row in selected if row["run_index"] == run_index]
            run_metric = _metric(
                sum(row["tp_ev"] for row in run_rows),
                sum(row["fp"] for row in run_rows),
                sum(row["fn"] for row in run_rows),
            )[2]
            if run_metric is None:
                raise ValueError("run-specific F1 is undefined")
            run_f1.append(run_metric)
        output.append(
            {
                "condition_id": condition_id,
                "condition": CONDITION_LABELS[condition_id],
                "backbone": BACKBONES[condition_id],
                "complete": statuses["complete"],
                "failed": statuses["failed"],
                "refused": statuses["refusal"],
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "mean_run_f1": float(np.mean(np.asarray(run_f1, dtype=np.float64))),
                "pooled_count_f1": pooled_f1,
            }
        )
    return output


def subgroup_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for condition_id in CONDITION_ORDER:
        for stratum in STRATUM_ORDER:
            selected = [
                row
                for row in rows
                if row["condition_id"] == condition_id and row["stratum"] == stratum
            ]
            tp = sum(row["tp_ev"] for row in selected)
            fp = sum(row["fp"] for row in selected)
            fn = sum(row["fn"] for row in selected)
            precision, recall, f1 = _metric(tp, fp, fn)
            output.append(
                {
                    "condition_id": condition_id,
                    "condition": CONDITION_LABELS[condition_id],
                    "stratum": STRATUM_LABELS[stratum],
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "cells": len(selected),
                }
            )
    return output


def retrieval_window_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    windows = STRATUM_ORDER[:3]
    for condition_id in ("qwen_fixed_team", "qwen_without_retrieval"):
        for window in windows:
            selected = [
                row
                for row in rows
                if row["condition_id"] == condition_id
                and row["stratum"] == window
                and row["positive_reference_count"] == 1
            ]
            denominator = sum(row["tp_ev"] + row["fn"] for row in selected)
            if denominator != 20:
                raise ValueError("recent-KEV window denominator differs from 20")
            output.append(
                {
                    "condition_id": condition_id,
                    "condition": CONDITION_LABELS[condition_id],
                    "window": STRATUM_LABELS[window].split(", ", 1)[1],
                    "affected_target_recall": sum(row["tp_ev"] for row in selected)
                    / denominator,
                    "positive_cells": len(selected),
                    "independent_families": len({row["family_id"] for row in selected}),
                }
            )
    return output


def _family_cube(
    rows: list[dict[str, Any]],
    conditions: tuple[str, ...],
    *,
    endpoint: Literal["f1", "recent_recall"],
) -> tuple[NDArray[np.int64], tuple[str, ...]]:
    if endpoint == "recent_recall":
        selected = [
            row
            for row in rows
            if row["condition_id"] in conditions
            and row["stratum"] in STRATUM_ORDER[:3]
            and row["positive_reference_count"] == 1
        ]
        width = 2
    else:
        selected = [row for row in rows if row["condition_id"] in conditions]
        width = 3
    family_strata: dict[str, str] = {}
    grouped: dict[tuple[str, str, int], list[int]] = defaultdict(
        lambda: [0 for _ in range(width)]
    )
    for row in selected:
        family_strata.setdefault(row["family_id"], row["stratum"])
        key = (row["family_id"], row["condition_id"], row["run_index"])
        grouped[key][0] += row["tp_ev"]
        if endpoint == "recent_recall":
            grouped[key][1] += row["fn"]
        else:
            grouped[key][1] += row["fp"]
            grouped[key][2] += row["fn"]
    families = tuple(sorted(family_strata))
    if endpoint == "recent_recall":
        if Counter(family_strata.values()) != Counter(
            {"recent_kev_0_30": 4, "recent_kev_31_60": 4, "recent_kev_61_90": 4}
        ):
            raise ValueError("recent-KEV family allocation differs")
    elif Counter(family_strata.values()) != Counter(EXPECTED_FAMILY_STRATA):
        raise ValueError("family allocation differs")
    family_index = {family: index for index, family in enumerate(families)}
    condition_index = {condition: index for index, condition in enumerate(conditions)}
    cube = np.full((len(conditions), 5, len(families), width), -1, dtype=np.int64)
    for (family, condition, run_index), values in grouped.items():
        location = (condition_index[condition], run_index - 1, family_index[family])
        if np.any(cube[location] >= 0):
            raise ValueError("duplicate family/condition/repetition count")
        cube[location] = values
    if np.any(cube < 0):
        raise ValueError("paired count cube is incomplete")
    return cube, tuple(family_strata[family] for family in families)


def _draws(strata: tuple[str, ...], *, seed: int) -> Draws:
    rng = np.random.default_rng(seed)
    weights = np.zeros((RESAMPLES, len(strata)), dtype=np.int64)
    strata_array = np.asarray(strata, dtype=np.str_)
    for stratum in sorted(set(strata)):
        members = np.flatnonzero(strata_array == stratum).astype(np.int64, copy=False)
        sampled = rng.choice(members, size=(RESAMPLES, len(members)), replace=True)
        draw_rows = np.repeat(np.arange(RESAMPLES, dtype=np.int64), len(members))
        np.add.at(weights, (draw_rows, sampled.reshape(-1)), 1)
    run_indices = rng.integers(0, 5, size=(RESAMPLES, 5), dtype=np.int64)
    return Draws(weights, run_indices)


def _metric_distribution(
    condition_cube: NDArray[np.int64],
    *,
    draws: Draws,
    endpoint: Literal["f1", "recent_recall"],
) -> NDArray[np.float64]:
    estimates = np.zeros(RESAMPLES, dtype=np.float64)
    for position in range(5):
        selected = condition_cube[draws.run_indices[:, position], :, :]
        pooled = np.einsum("bf,bfk->bk", draws.family_weights, selected, optimize=True)
        if endpoint == "f1":
            denominator = 2 * pooled[:, 0] + pooled[:, 1] + pooled[:, 2]
            numerator = 2.0 * pooled[:, 0]
        else:
            denominator = pooled[:, 0] + pooled[:, 1]
            numerator = pooled[:, 0].astype(np.float64)
        if np.any(denominator <= 0):
            raise ValueError("bootstrap metric has a zero denominator")
        estimates += numerator / denominator
    return estimates / 5.0


def _point_metric(
    condition_cube: NDArray[np.int64], *, endpoint: Literal["f1", "recent_recall"]
) -> float:
    run_values: list[float] = []
    for run_index in range(5):
        pooled = np.sum(condition_cube[run_index], axis=0, dtype=np.int64)
        if endpoint == "f1":
            denominator = int(2 * pooled[0] + pooled[1] + pooled[2])
            numerator = float(2 * pooled[0])
        else:
            denominator = int(pooled[0] + pooled[1])
            numerator = float(pooled[0])
        if denominator <= 0:
            raise ValueError("point metric has a zero denominator")
        run_values.append(numerator / denominator)
    return float(np.mean(np.asarray(run_values, dtype=np.float64)))


def _contrast(
    cube: NDArray[np.int64],
    intervention_index: int,
    comparator_index: int,
    *,
    draws: Draws,
    endpoint: Literal["f1", "recent_recall"],
) -> Contrast:
    point = _point_metric(cube[intervention_index], endpoint=endpoint) - _point_metric(
        cube[comparator_index], endpoint=endpoint
    )
    deltas = _metric_distribution(
        cube[intervention_index], draws=draws, endpoint=endpoint
    ) - _metric_distribution(cube[comparator_index], draws=draws, endpoint=endpoint)
    interval = np.quantile(deltas, (0.025, 0.975), method="linear")
    centered = deltas - point
    extreme = int(np.count_nonzero(np.abs(centered) >= abs(point)))
    raw_p = float((extreme + 1) / (RESAMPLES + 1))
    return Contrast(float(point), float(interval[0]), float(interval[1]), raw_p, deltas)


def _holm(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, (identifier, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * p_value))
        adjusted[identifier] = running
    return adjusted


def statistical_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    main_conditions = (
        "qwen_fixed_team",
        "qwen_single_rag",
        "qwen_without_evidence_check",
        "gemma_fixed_team",
        "gemma_single_rag",
        "gpt_oss_fixed_team",
        "gpt_oss_single_rag",
    )
    cube, strata = _family_cube(rows, main_conditions, endpoint="f1")
    main_draws = _draws(strata, seed=MAIN_SEED)
    main_index = {condition: index for index, condition in enumerate(main_conditions)}

    fixed_single = _contrast(
        cube,
        main_index["qwen_fixed_team"],
        main_index["qwen_single_rag"],
        draws=main_draws,
        endpoint="f1",
    )
    evidence = _contrast(
        cube,
        main_index["qwen_fixed_team"],
        main_index["qwen_without_evidence_check"],
        draws=main_draws,
        endpoint="f1",
    )
    gemma = _contrast(
        cube,
        main_index["gemma_fixed_team"],
        main_index["gemma_single_rag"],
        draws=main_draws,
        endpoint="f1",
    )
    gpt_oss = _contrast(
        cube,
        main_index["gpt_oss_fixed_team"],
        main_index["gpt_oss_single_rag"],
        draws=main_draws,
        endpoint="f1",
    )
    qwen_gemma = _contrast(
        cube,
        main_index["qwen_fixed_team"],
        main_index["gemma_fixed_team"],
        draws=main_draws,
        endpoint="f1",
    )
    qwen_gpt = _contrast(
        cube,
        main_index["qwen_fixed_team"],
        main_index["gpt_oss_fixed_team"],
        draws=main_draws,
        endpoint="f1",
    )

    recall_conditions = ("qwen_fixed_team", "qwen_without_retrieval")
    recall_cube, recall_strata = _family_cube(
        rows, recall_conditions, endpoint="recent_recall"
    )
    retrieval = _contrast(
        recall_cube,
        0,
        1,
        draws=_draws(recall_strata, seed=MAIN_SEED),
        endpoint="recent_recall",
    )

    ablation_adjusted = _holm(
        {"evidence_checking": evidence.raw_p, "retrieval": retrieval.raw_p}
    )
    backbone_adjusted = _holm(
        {"qwen_vs_gemma": qwen_gemma.raw_p, "qwen_vs_gpt_oss": qwen_gpt.raw_p}
    )

    minimum_distribution = np.min(
        np.vstack((fixed_single.distribution, gemma.distribution, gpt_oss.distribution)),
        axis=0,
    )
    minimum_interval = np.quantile(
        minimum_distribution, (0.025, 0.975), method="linear"
    )

    autonomous_conditions = (
        "qwen_autonomous_team",
        "qwen_fixed_team",
        "qwen_single_rag",
    )
    autonomous_cube, autonomous_strata = _family_cube(
        rows, autonomous_conditions, endpoint="f1"
    )
    autonomous_draws = _draws(autonomous_strata, seed=AUTONOMOUS_SEED)
    autonomous_fixed = _contrast(
        autonomous_cube, 0, 1, draws=autonomous_draws, endpoint="f1"
    )
    autonomous_single = _contrast(
        autonomous_cube, 0, 2, draws=autonomous_draws, endpoint="f1"
    )

    summary = {item["condition_id"]: item for item in condition_summary(rows)}
    context_effect = (
        summary["qwen_fixed_team"]["mean_run_f1"]
        - summary["qwen_without_context_role"]["mean_run_f1"]
    )

    def record(
        identifier: str,
        label: str,
        endpoint: str,
        contrast: Contrast,
        *,
        adjusted_p: float | None,
        status: str,
        interpretation: str,
        seed: int,
    ) -> dict[str, Any]:
        return {
            "comparison_id": identifier,
            "comparison": label,
            "endpoint": endpoint,
            "effect": contrast.effect,
            "ci_lower": contrast.ci_lower,
            "ci_upper": contrast.ci_upper,
            "raw_p": contrast.raw_p,
            "adjusted_p": adjusted_p,
            "analysis_status": status,
            "interpretation": interpretation,
            "resamples": RESAMPLES,
            "rng_seed": seed,
        }

    comparisons = [
        record(
            "qwen_fixed_vs_single",
            "Qwen fixed team versus single-RAG",
            "Evidence-verified detection F1",
            fixed_single,
            adjusted_p=None,
            status="Confirmatory",
            interpretation="No evidence of improved F1",
            seed=MAIN_SEED,
        ),
        record(
            "evidence_checking_retained_vs_removed",
            "Evidence checking retained versus removed",
            "Evidence-verified detection F1",
            evidence,
            adjusted_p=ablation_adjusted["evidence_checking"],
            status="Multiplicity-adjusted",
            interpretation="No observed difference",
            seed=MAIN_SEED,
        ),
        record(
            "retrieval_retained_vs_removed",
            "Retrieval retained versus removed",
            "Recent-KEV affected-target recall",
            retrieval,
            adjusted_p=ablation_adjusted["retrieval"],
            status="Multiplicity-adjusted",
            interpretation="Retrieval benefit supported",
            seed=MAIN_SEED,
        ),
        {
            "comparison_id": "context_role_retained_vs_removed",
            "comparison": "Clinical-context agent retained versus removed",
            "endpoint": "Evidence-verified detection F1",
            "effect": context_effect,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "raw_p": None,
            "adjusted_p": None,
            "analysis_status": "Descriptive technical ablation",
            "interpretation": "No observed difference",
            "resamples": None,
            "rng_seed": None,
        },
        record(
            "gemma_fixed_vs_single",
            "Gemma fixed team versus single-RAG",
            "Evidence-verified detection F1",
            gemma,
            adjusted_p=None,
            status="Backbone component",
            interpretation="Direction uncertain",
            seed=MAIN_SEED,
        ),
        record(
            "gpt_oss_fixed_vs_single",
            "gpt-oss fixed team versus single-RAG",
            "Evidence-verified detection F1",
            gpt_oss,
            adjusted_p=None,
            status="Backbone component",
            interpretation="Positive direction; interval includes zero",
            seed=MAIN_SEED,
        ),
        {
            "comparison_id": "minimum_fixed_team_effect",
            "comparison": "Worst-case fixed-team effect across backbones",
            "endpoint": "Minimum evidence-verified F1 difference",
            "effect": min(fixed_single.effect, gemma.effect, gpt_oss.effect),
            "ci_lower": float(minimum_interval[0]),
            "ci_upper": float(minimum_interval[1]),
            "raw_p": None,
            "adjusted_p": None,
            "analysis_status": "Compound robustness estimate",
            "interpretation": "No consistent fixed-team advantage",
            "resamples": RESAMPLES,
            "rng_seed": MAIN_SEED,
        },
        record(
            "qwen_fixed_vs_gemma_fixed",
            "Qwen fixed team versus Gemma fixed team",
            "Evidence-verified detection F1",
            qwen_gemma,
            adjusted_p=backbone_adjusted["qwen_vs_gemma"],
            status="Multiplicity-adjusted",
            interpretation="Higher F1 with the tested Qwen configuration",
            seed=MAIN_SEED,
        ),
        record(
            "qwen_fixed_vs_gpt_oss_fixed",
            "Qwen fixed team versus gpt-oss fixed team",
            "Evidence-verified detection F1",
            qwen_gpt,
            adjusted_p=backbone_adjusted["qwen_vs_gpt_oss"],
            status="Multiplicity-adjusted",
            interpretation="Higher F1 with the tested Qwen configuration",
            seed=MAIN_SEED,
        ),
        record(
            "qwen_autonomous_vs_fixed",
            "Qwen autonomous team versus fixed team",
            "Evidence-verified detection F1",
            autonomous_fixed,
            adjusted_p=None,
            status="Confirmatory",
            interpretation="No evidence of superiority",
            seed=AUTONOMOUS_SEED,
        ),
        record(
            "qwen_autonomous_vs_single",
            "Qwen autonomous team versus single-RAG",
            "Evidence-verified detection F1",
            autonomous_single,
            adjusted_p=None,
            status="Descriptive comparison",
            interpretation="No evidence of a difference",
            seed=AUTONOMOUS_SEED,
        ),
    ]
    return {
        "schema_version": "public-statistical-results-1.0.0",
        "analysis_population": "all 3,000 scheduled cells",
        "failed_and_refused_cells_retained": True,
        "comparisons": comparisons,
    }


def _article_comparison_rows(statistics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in statistics["comparisons"]:
        rows.append(
            {
                "comparison": item["comparison"],
                "endpoint": item["endpoint"],
                "effect": item["effect"],
                "ci_lower": item["ci_lower"],
                "ci_upper": item["ci_upper"],
                "raw_p": item["raw_p"],
                "adjusted_p": item["adjusted_p"],
                "analysis_status": item["analysis_status"],
                "interpretation": item["interpretation"],
            }
        )
    return rows


def analyze(cell_path: Path) -> dict[str, Any]:
    rows = read_cells(cell_path)
    statistics = statistical_results(rows)
    return {
        "condition_summary": condition_summary(rows),
        "subgroup_results": subgroup_results(rows),
        "retrieval_window_recall": retrieval_window_results(rows),
        "statistical_results": statistics,
        "article_comparisons": _article_comparison_rows(statistics),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(output: Path, result: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(output / "condition_summary.csv", result["condition_summary"])
    _write_csv(output / "subgroup_results.csv", result["subgroup_results"])
    _write_csv(
        output / "retrieval_window_recall.csv", result["retrieval_window_recall"]
    )
    _write_csv(output / "article_comparisons.csv", result["article_comparisons"])
    (output / "statistical_results.json").write_text(
        json.dumps(result["statistical_results"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "AUTONOMOUS_SEED",
    "CONDITION_ORDER",
    "MAIN_SEED",
    "RESAMPLES",
    "analyze",
    "read_cells",
    "validate_cells",
    "write_outputs",
]
