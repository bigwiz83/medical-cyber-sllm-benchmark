from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from medcyber_benchmark.scoring import (
    CONDITION_IDS,
    CallSeed,
    FinalPrediction,
    jsonl_bytes,
    load_predictions,
    prediction_json_schema,
    score_predictions,
    validate_prediction_matrix,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "data" / "predictions" / "final_predictions.jsonl"
EXPECTED_SCORES = ROOT / "data" / "derived" / "integrated_cell_scores.jsonl"
SCHEMA = ROOT / "schemas" / "final_prediction.schema.json"
PROVENANCE = ROOT / "metadata" / "prediction_provenance.json"


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prediction_inventory_state_and_seed_contract() -> None:
    rows = load_predictions(PREDICTIONS)
    assert len(rows) == 3_000
    assert Counter(item.condition_id for item in rows) == Counter(
        {condition: 300 for condition in CONDITION_IDS}
    )
    assert Counter(item.run_status for item in rows) == Counter(
        {"complete": 2_759, "failed": 236, "refusal": 5}
    )
    assert len({(item.condition_id, item.blind_case_id, item.run_index) for item in rows}) == 3_000
    assert all(
        tuple(seed.call_slot for seed in item.call_seed_schedule) == (1, 2, 3, 4, 5)
        for item in rows
    )
    schedules_by_case_run: dict[tuple[str, int], tuple[int, ...]] = {}
    explicit_verification_status = 0
    omitted_verification_status = 0
    for item in rows:
        key = (item.blind_case_id, item.run_index)
        schedule = tuple(seed.seed for seed in item.call_seed_schedule)
        assert schedules_by_case_run.setdefault(key, schedule) == schedule
        assert len(set(item.retrieved_object_ids)) == len(item.retrieved_object_ids)
        if item.condition_id == "qwen_without_retrieval":
            assert item.retrieved_object_ids == ()
        if item.run_status == "failed":
            assert item.final_output is None
        elif item.run_status == "complete":
            assert item.final_output is not None and item.final_output.status == "ok"
        else:
            assert item.final_output is not None and item.final_output.status == "refusal"
        for finding in () if item.final_output is None else item.final_output.findings:
            cited_objects = {
                evidence_id
                for evidence_id in finding.evidence_ids
                if evidence_id.startswith("obj_")
            }
            assert cited_objects.issubset(set(item.retrieved_object_ids))
            if "verification_status" in finding.model_fields_set:
                explicit_verification_status += 1
            else:
                omitted_verification_status += 1
    assert len(schedules_by_case_run) == 300
    assert explicit_verification_status == 546
    assert omitted_verification_status == 415


def test_prediction_schema_is_generated_from_runtime_contract() -> None:
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == prediction_json_schema()


def test_prediction_provenance_hashes_and_canonical_seed_schedule() -> None:
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    assert provenance["artifacts"]["prediction_sha256"] == _sha256(PREDICTIONS)
    assert provenance["artifacts"]["prediction_schema_sha256"] == _sha256(SCHEMA)
    assert provenance["artifacts"]["scorer_sha256"] == _sha256(
        ROOT / "src" / "medcyber_benchmark" / "scoring.py"
    )
    rows = load_predictions(PREDICTIONS)
    schedules: dict[tuple[str, int], tuple[CallSeed, ...]] = {}
    for item in rows:
        schedules.setdefault((item.blind_case_id, item.run_index), item.call_seed_schedule)
    entries = [
        {
            "blind_case_id": blind_case_id,
            "run_index": run_index,
            "call_slot": item.call_slot,
            "seed": item.seed,
        }
        for (blind_case_id, run_index), schedule in sorted(schedules.items())
        for item in schedule
    ]
    canonical = json.dumps(
        entries,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert len(entries) == 1_500
    assert hashlib.sha256(canonical).hexdigest() == provenance["seed_schedule"][
        "canonical_schedule_sha256"
    ]


def test_failed_and_refusal_outputs_cannot_be_salvaged() -> None:
    base = load_predictions(PREDICTIONS)[0].model_dump(mode="json")
    base["run_status"] = "failed"
    with pytest.raises(ValidationError):
        FinalPrediction.model_validate(base)
    base["run_status"] = "refusal"
    with pytest.raises(ValidationError):
        FinalPrediction.model_validate(base)


def test_unretrieved_corpus_citation_is_rejected() -> None:
    source = next(
        item
        for item in load_predictions(PREDICTIONS)
        if item.final_output is not None
        and any(
            evidence_id.startswith("obj_")
            for finding in item.final_output.findings
            for evidence_id in finding.evidence_ids
        )
    )
    payload = source.model_dump(mode="json", exclude_unset=True)
    payload["retrieved_object_ids"] = []
    with pytest.raises(ValidationError):
        FinalPrediction.model_validate(payload)


def test_generic_matrix_validation_allows_new_terminal_totals() -> None:
    rows = list(load_predictions(PREDICTIONS))
    replacement = rows[0].model_dump(mode="json", exclude_unset=True)
    replacement["run_status"] = "failed"
    replacement["final_output"] = None
    rows[0] = FinalPrediction.model_validate(replacement)
    blind_case_ids = tuple(sorted({item.blind_case_id for item in rows}))
    validate_prediction_matrix(
        rows,
        conditions=CONDITION_IDS,
        blind_case_ids=blind_case_ids,
    )


def test_offline_rescore_is_exactly_the_released_matrix() -> None:
    rescored = score_predictions(ROOT, PREDICTIONS)
    expected = _read_jsonl(EXPECTED_SCORES)
    assert rescored == expected
    assert jsonl_bytes(rescored) == EXPECTED_SCORES.read_bytes()
