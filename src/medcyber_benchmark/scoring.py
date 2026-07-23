from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONDITION_IDS = (
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
ConditionId = Literal[
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
]
RunStatus = Literal["complete", "failed", "refusal"]
MAX_JSONL_BYTES = 8 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 2 * 1024 * 1024


class ScoringError(RuntimeError):
    """Raised when a public scoring input or integrity binding is invalid."""


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CallSeed(ContractModel):
    call_slot: int = Field(strict=True, ge=1, le=5)
    seed: int = Field(strict=True, ge=0, le=4_294_967_295)


class Applicability(ContractModel):
    product_or_control: str = Field(strict=True, min_length=1, max_length=2_048)
    installed_or_observed_state: str = Field(strict=True, min_length=1, max_length=2_048)
    affected_or_required_state: str = Field(strict=True, min_length=1, max_length=2_048)
    exposure: Literal["exposed", "not_exposed", "unknown", "not_applicable"]
    prerequisites: Literal["met", "not_met", "unknown", "not_applicable"]
    rationale: str = Field(strict=True, min_length=1, max_length=2_048)


class Finding(ContractModel):
    finding_type: Literal["cve", "synthetic_misconfiguration"]
    target_key: str = Field(
        strict=True,
        max_length=128,
        pattern=r"^(?:CVE-[0-9]{4}-[0-9]{4,}|MCFG\.[A-Z0-9][A-Z0-9_.-]*)$",
    )
    asset_id: str = Field(strict=True, min_length=1, max_length=128)
    affected_status: Literal["affected", "not_affected", "insufficient_evidence"]
    applicability: Applicability
    evidence_ids: tuple[
        str,
        ...,
    ] = Field(min_length=1, max_length=16)
    verification_status: Literal["verified"] | None = None

    @model_validator(mode="after")
    def validate_identity_and_evidence(self) -> Finding:
        if self.finding_type == "cve" and not self.target_key.startswith("CVE-"):
            raise ValueError("CVE findings require a CVE target key")
        if self.finding_type == "synthetic_misconfiguration" and not self.target_key.startswith(
            "MCFG."
        ):
            raise ValueError("synthetic misconfiguration findings require an MCFG target key")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence identifiers must be unique")
        for evidence_id in self.evidence_ids:
            if not _valid_evidence_id(evidence_id):
                raise ValueError(f"invalid evidence identifier: {evidence_id}")
        return self


class FinalOutput(ContractModel):
    status: Literal["ok", "refusal"]
    findings: tuple[Finding, ...] = Field(default=(), max_length=32)
    refusal_reason: str | None = Field(default=None, strict=True, min_length=1, max_length=2_048)

    @model_validator(mode="after")
    def validate_atomic_output(self) -> FinalOutput:
        if self.status == "ok" and self.refusal_reason is not None:
            raise ValueError("successful output cannot include a refusal reason")
        if self.status == "refusal" and (self.findings or self.refusal_reason is None):
            raise ValueError("refusal output requires a reason and no findings")
        return self


class FinalPrediction(ContractModel):
    schema_version: Literal["public-final-prediction-1.0.0"]
    condition_id: ConditionId
    blind_case_id: str = Field(strict=True, pattern=r"^bc_[a-f0-9]{32}$")
    run_index: int = Field(strict=True, ge=1, le=5)
    run_status: RunStatus
    call_seed_schedule: tuple[CallSeed, CallSeed, CallSeed, CallSeed, CallSeed]
    retrieved_object_ids: tuple[str, ...] = Field(max_length=32)
    final_output: FinalOutput | None

    @model_validator(mode="after")
    def validate_state_and_schedule(self) -> FinalPrediction:
        if tuple(item.call_slot for item in self.call_seed_schedule) != (1, 2, 3, 4, 5):
            raise ValueError("call seed schedule must contain ordered slots 1 through 5")
        if len(set(self.retrieved_object_ids)) != len(self.retrieved_object_ids):
            raise ValueError("retrieved object identifiers must be unique")
        if any(
            not object_id.startswith("obj_") or not _valid_evidence_id(object_id)
            for object_id in self.retrieved_object_ids
        ):
            raise ValueError("retrieved object identifiers must be valid obj_ identifiers")
        if self.condition_id == "qwen_without_retrieval" and self.retrieved_object_ids:
            raise ValueError("the without-retrieval condition cannot contain retrieved objects")
        if self.run_status == "complete":
            if self.final_output is None or self.final_output.status != "ok":
                raise ValueError("complete run requires one successful final output")
        elif self.run_status == "refusal":
            if self.final_output is None or self.final_output.status != "refusal":
                raise ValueError("refusal run requires one refusal final output")
        elif self.final_output is not None:
            raise ValueError("failed run cannot retain a final output")
        cited_objects = {
            evidence_id
            for finding in (() if self.final_output is None else self.final_output.findings)
            for evidence_id in finding.evidence_ids
            if evidence_id.startswith("obj_")
        }
        if not cited_objects.issubset(set(self.retrieved_object_ids)):
            raise ValueError("cited corpus objects must occur in retrieved_object_ids")
        return self


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    evidence_id: str
    path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class CaseEvidenceIndex:
    artifacts: Mapping[str, EvidenceArtifact]


def _valid_evidence_id(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 36:
        return False
    if not (value.startswith("obj_") or value.startswith("art_")):
        return False
    return all(character in "0123456789abcdef" for character in value[4:])


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@cache
def _cached_sha256(path_text: str) -> str:
    return sha256_file(Path(path_text))


def _strict_json_loads(payload: str, noun: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite constant: {value}")
            ),
            object_pairs_hook=reject_duplicates,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ScoringError(f"invalid strict JSON in {noun}: {exc}") from exc


def _load_json(path: Path, noun: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ScoringError(f"cannot read {noun}: {path}") from exc
    return _strict_json_loads(text, noun)


def load_predictions(path: Path) -> tuple[FinalPrediction, ...]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ScoringError("prediction JSONL is missing or empty")
    if path.stat().st_size > MAX_JSONL_BYTES:
        raise ScoringError("prediction JSONL exceeds the fixed size ceiling")
    rows: list[FinalPrediction] = []
    with path.open("rb") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if len(raw) > MAX_JSONL_LINE_BYTES:
                raise ScoringError(f"prediction line {line_number} exceeds the size ceiling")
            if not raw.endswith(b"\n") or not raw.strip():
                raise ScoringError("every prediction row must be nonblank and end with LF")
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ScoringError("prediction JSONL must be UTF-8") from exc
            payload = _strict_json_loads(text, f"prediction line {line_number}")
            try:
                rows.append(FinalPrediction.model_validate(payload))
            except ValueError as exc:
                raise ScoringError(
                    f"prediction line {line_number} violates the public schema: {exc}"
                ) from exc
    return tuple(rows)


def validate_prediction_matrix(
    predictions: Sequence[FinalPrediction],
    *,
    conditions: Sequence[str],
    blind_case_ids: Sequence[str],
) -> None:
    if tuple(conditions) != CONDITION_IDS:
        raise ScoringError("condition registry order differs from the public scoring contract")
    if len(predictions) != 3_000:
        raise ScoringError(f"expected 3,000 prediction rows, found {len(predictions)}")
    expected = {
        (condition, blind_case_id, run_index)
        for condition in conditions
        for run_index in range(1, 6)
        for blind_case_id in blind_case_ids
    }
    observed = [
        (item.condition_id, item.blind_case_id, item.run_index) for item in predictions
    ]
    if len(set(observed)) != len(observed):
        raise ScoringError("prediction matrix contains duplicate keys")
    if set(observed) != expected:
        raise ScoringError("prediction matrix is incomplete or contains unexpected keys")
    schedules: dict[tuple[str, int], tuple[int, ...]] = {}
    for item in predictions:
        key = (item.blind_case_id, item.run_index)
        schedule = tuple(entry.seed for entry in item.call_seed_schedule)
        prior = schedules.setdefault(key, schedule)
        if prior != schedule:
            raise ScoringError("paired conditions do not share the same call-slot seeds")


def _safe_path(root: Path, relative: str, noun: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or "\\" in relative:
        raise ScoringError(f"unsafe {noun} path")
    target = (root / posix).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ScoringError(f"missing or escaped {noun} path: {relative}")
    return target


@cache
def _resolve_reference_artifact(release_root: Path, original_path: str) -> Path:
    """Resolve a frozen source-tree path through the finite public projection map."""

    if "\\" in original_path or ".." in PurePosixPath(original_path).parts:
        raise ScoringError("unsafe frozen reference path")
    generated = "research/generated/eval60-confirmatory-v1-20260720/"
    cve_sources = "research/sources/raw/cve_program/"
    mappings = (
        (generated + "model_visible/", "data/benchmark/model_visible/"),
        (generated + "evaluator_only/", "data/benchmark/evaluator_only/"),
        (cve_sources, "data/sources/cve_program/"),
    )
    projected: str | None = None
    for prefix, replacement in mappings:
        if original_path.startswith(prefix):
            projected = replacement + original_path.removeprefix(prefix)
            break
    if original_path == "knowledge/raw/known_exploited_vulnerabilities.json":
        projected = "data/sources/known_exploited_vulnerabilities.json"
    elif original_path == "research/scenarios/blueprint.yaml":
        projected = "data/sources/blueprint.yaml"
    if projected is None:
        raise ScoringError(f"unmapped frozen reference path: {original_path}")
    return _safe_path(release_root, projected, "projected reference artifact")


@cache
def _verified_file_cached(
    root: Path, relative_path: str, size_bytes: int, sha256: str, noun: str
) -> Path:
    path = _safe_path(root, relative_path, noun)
    if path.stat().st_size != size_bytes:
        raise ScoringError(f"{noun} size differs: {path}")
    if _cached_sha256(str(path)) != sha256:
        raise ScoringError(f"{noun} hash differs: {path}")
    return path


def _verified_file(root: Path, record: Mapping[str, Any], noun: str) -> Path:
    return _verified_file_cached(
        root,
        str(record["relative_path"]),
        int(record["size_bytes"]),
        str(record["sha256"]),
        noun,
    )


def _build_evidence_index(benchmark_root: Path, blind_case_id: str) -> CaseEvidenceIndex:
    case_root = benchmark_root / "model_visible" / "cases" / blind_case_id
    scenario_path = case_root / "scenario.json"
    scenario = cast(Mapping[str, Any], _load_json(scenario_path, "model-visible scenario"))
    if scenario.get("blind_case_id") != blind_case_id:
        raise ScoringError("scenario blind-case identifier differs from its directory")
    artifacts: dict[str, EvidenceArtifact] = {}
    for field in (
        "raw_asset_refs",
        "inventory_refs",
        "configuration_refs",
        "sbom_refs",
        "topology_refs",
    ):
        for record in cast(Sequence[Mapping[str, Any]], scenario.get(field, [])):
            path = _verified_file(benchmark_root, record, "input artifact")
            evidence_id = str(record["artifact_id"])
            artifacts[evidence_id] = EvidenceArtifact(
                evidence_id=evidence_id, path=path, sha256=str(record["sha256"])
            )
    corpus_ref = cast(Mapping[str, Any], scenario["corpus_manifest_ref"])
    corpus_path = _verified_file(benchmark_root, corpus_ref, "corpus manifest")
    corpus = cast(Mapping[str, Any], _load_json(corpus_path, "corpus manifest"))
    if corpus.get("blind_case_id") != blind_case_id:
        raise ScoringError("corpus blind-case identifier differs from the scenario")
    for record in cast(Sequence[Mapping[str, Any]], corpus["objects"]):
        path = _verified_file(benchmark_root, record, "corpus object")
        evidence_id = str(record["corpus_object_id"])
        artifacts[evidence_id] = EvidenceArtifact(
            evidence_id=evidence_id, path=path, sha256=str(record["sha256"])
        )
    return CaseEvidenceIndex(artifacts=artifacts)


@cache
def _load_locked_json(path_text: str, expected_sha256: str) -> Any:
    path = Path(path_text)
    if _cached_sha256(path_text) != expected_sha256:
        raise ScoringError(f"evidence artifact hash changed: {path}")
    return _load_json(path, "evidence artifact")


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ScoringError("reference JSON Pointer must be absolute")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            mapping = cast(Mapping[str, Any], current)
            if token not in mapping:
                raise ScoringError(f"reference JSON Pointer does not resolve: {pointer}")
            current = mapping[token]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            if not token.isdigit() or int(token) >= len(current):
                raise ScoringError(f"reference JSON Pointer index is invalid: {pointer}")
            current = current[int(token)]
        else:
            raise ScoringError(f"reference JSON Pointer traverses a scalar: {pointer}")
    return current


@cache
def _selected_content_sha256(path_text: str, artifact_sha256: str, pointer: str) -> str:
    selected = _resolve_json_pointer(
        _load_locked_json(path_text, artifact_sha256), pointer
    )
    return hashlib.sha256(canonical_json_bytes(selected)).hexdigest()


def _alternative_satisfied(
    path: Path, artifact_sha256: str, alternative: Mapping[str, Any]
) -> bool:
    if artifact_sha256 != alternative["artifact_sha256"]:
        return False
    locator = cast(Mapping[str, Any], alternative["locator"])
    if locator.get("kind") != "json_pointer":
        raise ScoringError("the public scorer accepts only frozen JSON Pointer evidence")
    selected_sha256 = _selected_content_sha256(
        str(path), artifact_sha256, str(locator["expression"])
    )
    return selected_sha256 == str(alternative["selected_content_sha256"])


def _requirement_satisfied(
    requirement: Mapping[str, Any],
    *,
    cited: Sequence[EvidenceArtifact],
    release_root: Path,
) -> bool:
    alternatives = cast(Sequence[Mapping[str, Any]], requirement["alternatives"])
    projected = [
        _resolve_reference_artifact(release_root, str(alternative["artifact_path"]))
        for alternative in alternatives
    ]
    for path, alternative in zip(projected, alternatives, strict=True):
        if _cached_sha256(str(path)) != alternative["artifact_sha256"]:
            raise ScoringError(f"projected reference artifact hash differs: {path}")
    if requirement["citation_scope"] == "evaluator_internal_only":
        return any(
            _alternative_satisfied(path, _cached_sha256(str(path)), alternative)
            for path, alternative in zip(projected, alternatives, strict=True)
        )
    return any(
        _alternative_satisfied(artifact.path, artifact.sha256, alternative)
        for alternative in alternatives
        for artifact in cited
    )


def _edge_failures(
    finding: Finding,
    reference: Mapping[str, Any],
    *,
    evidence_index: CaseEvidenceIndex,
    release_root: Path,
    retrieved_object_ids: frozenset[str],
) -> tuple[str, ...]:
    failures: list[str] = []
    if finding.affected_status != "affected":
        failures.append("not_affected_assertion")
    if reference["reference_label"] != "affected":
        failures.append("reference_not_affected")
    if reference["primary_endpoint_role"] != "positive":
        failures.append("reference_not_primary_positive")
    if finding.target_key != reference["target_key"]:
        failures.append("target_key")
    if finding.asset_id != reference["asset_id"]:
        failures.append("asset_id")
    if finding.finding_type != reference["finding_type"]:
        failures.append("finding_type")
    cited: list[EvidenceArtifact] = []
    for evidence_id in finding.evidence_ids:
        artifact = evidence_index.artifacts.get(evidence_id)
        if evidence_id.startswith("obj_") and evidence_id not in retrieved_object_ids:
            failures.append(f"not_retrieved:{evidence_id}")
        elif artifact is None:
            failures.append(f"unknown_evidence:{evidence_id}")
        else:
            cited.append(artifact)
    if not failures:
        for requirement in cast(
            Sequence[Mapping[str, Any]], reference["evidence_requirements"]
        ):
            if not _requirement_satisfied(
                requirement, cited=cited, release_root=release_root
            ):
                failures.append(f"evidence:{requirement['requirement_id']}")
    return tuple(failures)


def _prediction_id(finding: Finding, occurrence: int) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes(finding.model_dump(mode="json", exclude_unset=True))
    ).hexdigest()[:24]
    return f"PRED-{digest}-{occurrence:02d}"


def _maximum_matching(edges: Mapping[str, tuple[str, ...]]) -> Mapping[str, str]:
    matched_reference: dict[str, str] = {}

    def augment(prediction_id: str, visited: set[str]) -> bool:
        for candidate_id in edges[prediction_id]:
            if candidate_id in visited:
                continue
            visited.add(candidate_id)
            previous = matched_reference.get(candidate_id)
            if previous is None or augment(previous, visited):
                matched_reference[candidate_id] = prediction_id
                return True
        return False

    for prediction_id in sorted(edges):
        augment(prediction_id, set())
    return {
        prediction_id: candidate_id for candidate_id, prediction_id in matched_reference.items()
    }


def _score_cell(
    prediction: FinalPrediction,
    reference_scenario: Mapping[str, Any],
    evidence_index: CaseEvidenceIndex,
    release_root: Path,
) -> tuple[int, int, int, int]:
    positive_references = tuple(
        sorted(
            (
                item
                for item in cast(
                    Sequence[Mapping[str, Any]], reference_scenario["reference_items"]
                )
                if item["primary_endpoint_role"] == "positive"
                and item["reference_label"] == "affected"
            ),
            key=lambda item: str(item["candidate_id"]),
        )
    )
    findings: tuple[Finding, ...] = ()
    if (
        prediction.run_status == "complete"
        and prediction.final_output is not None
        and prediction.final_output.status == "ok"
    ):
        findings = tuple(
            item
            for item in prediction.final_output.findings
            if item.affected_status == "affected"
            and item.finding_type in {"cve", "synthetic_misconfiguration"}
        )
    occurrence_by_digest: dict[str, int] = defaultdict(int)
    prediction_rows: list[tuple[str, Finding]] = []
    for finding in findings:
        digest = hashlib.sha256(
            canonical_json_bytes(finding.model_dump(mode="json", exclude_unset=True))
        ).hexdigest()
        occurrence_by_digest[digest] += 1
        prediction_rows.append((_prediction_id(finding, occurrence_by_digest[digest]), finding))
    prediction_rows.sort(key=lambda item: item[0])
    references_by_id = {str(item["candidate_id"]): item for item in positive_references}
    edges: dict[str, tuple[str, ...]] = {}
    for prediction_id, finding in prediction_rows:
        edges[prediction_id] = tuple(
            candidate_id
            for candidate_id, reference in sorted(references_by_id.items())
            if not _edge_failures(
                finding,
                reference,
                evidence_index=evidence_index,
                release_root=release_root,
                retrieved_object_ids=frozenset(prediction.retrieved_object_ids),
            )
        )
    matched = _maximum_matching(edges)
    tp_ev = len(matched)
    return len(positive_references), tp_ev, len(prediction_rows) - tp_ev, len(
        positive_references
    ) - tp_ev


def score_predictions(root: Path, prediction_path: Path | None = None) -> list[dict[str, Any]]:
    root = root.resolve()
    benchmark_root = root / "data" / "benchmark"
    prediction_path = prediction_path or root / "data" / "predictions" / "final_predictions.jsonl"
    conditions_payload = cast(
        Mapping[str, Any], _load_json(root / "configs" / "conditions.json", "condition registry")
    )
    conditions = cast(Sequence[Mapping[str, Any]], conditions_payload["conditions"])
    condition_ids = tuple(str(item["condition_id"]) for item in conditions)
    condition_by_id = {str(item["condition_id"]): item for item in conditions}
    codebook = cast(
        Mapping[str, Any],
        _load_json(
            benchmark_root / "evaluator_only" / "blind_codebook.json", "blind codebook"
        ),
    )
    codebook_entries = cast(Sequence[Mapping[str, Any]], codebook["entries"])
    if len(codebook_entries) != 60:
        raise ScoringError("blind codebook must contain 60 entries")
    codebook_by_blind = {str(item["blind_case_id"]): item for item in codebook_entries}
    if len(codebook_by_blind) != 60:
        raise ScoringError("blind codebook identifiers are not unique")
    reference = cast(
        Mapping[str, Any],
        _load_json(
            benchmark_root / "evaluator_only" / "reference_standard.json",
            "reference standard",
        ),
    )
    reference_scenarios = cast(Sequence[Mapping[str, Any]], reference["scenarios"])
    reference_by_scenario = {str(item["scenario_id"]): item for item in reference_scenarios}
    if len(reference_by_scenario) != 60:
        raise ScoringError("reference standard must contain 60 unique scenarios")
    if {str(item["scenario_id"]) for item in codebook_entries} != set(reference_by_scenario):
        raise ScoringError("blind codebook and reference scenario sets differ")
    predictions = load_predictions(prediction_path)
    validate_prediction_matrix(
        predictions,
        conditions=condition_ids,
        blind_case_ids=tuple(codebook_by_blind),
    )
    prediction_by_key: dict[tuple[str, str, int], FinalPrediction] = {
        (item.condition_id, item.blind_case_id, item.run_index): item for item in predictions
    }
    evidence_by_blind = {
        blind_case_id: _build_evidence_index(benchmark_root, blind_case_id)
        for blind_case_id in sorted(codebook_by_blind)
    }
    rows: list[dict[str, Any]] = []
    scenario_order = sorted(reference_by_scenario)
    blind_by_scenario = {
        str(item["scenario_id"]): str(item["blind_case_id"]) for item in codebook_entries
    }
    for condition_id in condition_ids:
        condition = condition_by_id[condition_id]
        for run_index in range(1, 6):
            for scenario_id in scenario_order:
                blind_case_id = blind_by_scenario[scenario_id]
                prediction = prediction_by_key[(condition_id, blind_case_id, run_index)]
                reference_scenario = reference_by_scenario[scenario_id]
                positive_count, tp_ev, fp, fn = _score_cell(
                    prediction,
                    reference_scenario,
                    evidence_by_blind[blind_case_id],
                    root,
                )
                rows.append(
                    {
                        "condition_id": condition_id,
                        "condition": condition["display_name"],
                        "backbone": condition["backbone"],
                        "blind_case_id": blind_case_id,
                        "scenario_id": scenario_id,
                        "family_id": reference_scenario["scenario_family_id"],
                        "stratum": reference_scenario["stratum"],
                        "run_index": run_index,
                        "run_status": prediction.run_status,
                        "positive_reference_count": positive_count,
                        "tp_ev": tp_ev,
                        "fp": fp,
                        "fn": fn,
                    }
                )
    return rows


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(
        (
            json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        for row in rows
    )


def write_scores(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(jsonl_bytes(rows))
    os.replace(temporary, path)


def prediction_json_schema() -> dict[str, Any]:
    return FinalPrediction.model_json_schema()


__all__ = [
    "CONDITION_IDS",
    "CallSeed",
    "FinalOutput",
    "FinalPrediction",
    "Finding",
    "ScoringError",
    "jsonl_bytes",
    "load_predictions",
    "prediction_json_schema",
    "score_predictions",
    "validate_prediction_matrix",
    "write_scores",
]
