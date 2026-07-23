from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_PATH = PurePosixPath("metadata/release_manifest.json")
MAX_FILE_BYTES = 8 * 1024 * 1024
IGNORED_TOP_LEVEL = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "venv",
}
IGNORED_PARTS = {"__pycache__"}
EXCLUDED_PATH_PARTS = {
    "approval",
    "attempt",
    "authorization",
    "inflight",
    "invocations",
    "pilot",
    "raw",
    "state",
}
TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".lock",
    ".md",
    ".cjs",
    ".mjs",
    ".py",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
MEDIA_TYPES = {
    ".cff": "text/yaml",
    ".cjs": "text/javascript",
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".lock": "text/plain",
    ".md": "text/markdown",
    ".mjs": "text/javascript",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".py": "text/x-python",
    ".svg": "image/svg+xml",
    ".toml": "application/toml",
    ".txt": "text/plain",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
}

CVE_TERMS_URL = "https://www.cve.org/legal/termsofuse"
KEV_LICENSE_URL = "https://www.cisa.gov/sites/default/files/licenses/kev/license.txt"
SOURCE_NOTICE_MARKERS = (
    CVE_TERMS_URL,
    KEV_LICENSE_URL,
    "The MITRE Corporation",
    "CVE Usage",
    "CC0 1.0",
)
DATA_LICENSE_MARKERS = (
    "Creative Commons Attribution 4.0 International",
    "study-authored synthetic and derived material",
    *SOURCE_NOTICE_MARKERS,
)
MOJIBAKE_MARKERS = (
    chr(0xFFFD),
    chr(0xC9E4),
    "?" * 2 + "026",
    chr(0xC2) + chr(0xA9),
    chr(0xE2) + chr(0x20AC) + chr(0x201C),
    chr(0xE2) + chr(0x20AC) + chr(0x201D),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ignored(relative: PurePosixPath) -> bool:
    if not relative.parts:
        return False
    return (
        relative.parts[0] in IGNORED_TOP_LEVEL
        or relative.name == ".DS_Store"
        or any(part in IGNORED_PARTS for part in relative.parts)
        or any(part.endswith(".egg-info") for part in relative.parts)
    )


def release_files(root: Path, *, include_manifest: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if _ignored(relative):
            continue
        if path.is_symlink():
            files.append(path)
            continue
        if not path.is_file():
            continue
        if not include_manifest and relative == MANIFEST_PATH:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def manifest_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in release_files(root):
        relative = path.relative_to(root).as_posix()
        media_type = MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
        entries.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "media_type": media_type,
            }
        )
    return entries


def write_manifest(root: Path) -> Path:
    entries = manifest_entries(root)
    payload = {
        "schema_version": "public-release-manifest-1.0.0",
        "study_id": "MEDCYBER-SLLM-PAPER-01",
        "release_version": "1.0.2",
        "manifest_excludes_self": True,
        "file_count": len(entries),
        "total_size_bytes": sum(item["size_bytes"] for item in entries),
        "files": entries,
    }
    target = root / MANIFEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return target


def verify_manifest(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / MANIFEST_PATH
    if not path.is_file():
        return [f"missing manifest: {MANIFEST_PATH}"]
    try:
        observed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid manifest: {exc}"]
    expected_entries = manifest_entries(root)
    if observed.get("files") != expected_entries:
        errors.append("manifest file inventory or hashes differ from the release tree")
    if observed.get("file_count") != len(expected_entries):
        errors.append("manifest file_count differs")
    if observed.get("total_size_bytes") != sum(
        item["size_bytes"] for item in expected_entries
    ):
        errors.append("manifest total_size_bytes differs")
    return errors


def _public_text_patterns() -> list[tuple[str, re.Pattern[str]]]:
    return [
        ("legacy hypothesis label", re.compile(r"\b" + "H" + r"[1-8]\b")),
        ("unreleased brand label", re.compile("Cl" + "aude", re.IGNORECASE)),
        ("unreleased model label", re.compile("Fa" + "ble", re.IGNORECASE)),
        (
            "out-of-scope evaluator phrase",
            re.compile("human" + r"[- ]" + "clinician", re.IGNORECASE),
        ),
        (
            "out-of-scope evaluator phrase",
            re.compile("clinical" + r"[- ]" + "expert", re.IGNORECASE),
        ),
        (
            "internal condition token",
            re.compile("no" + "_" + "clinical", re.IGNORECASE),
        ),
        (
            "out-of-scope annotation field",
            re.compile("clinical" + "_" + "annotation", re.IGNORECASE),
        ),
        (
            "out-of-scope adjudication field",
            re.compile("human" + "_" + "adjudication", re.IGNORECASE),
        ),
        (
            "out-of-scope override phrase",
            re.compile("human" + r"[- ]" + "override", re.IGNORECASE),
        ),
        (
            "out-of-scope outcome phrase",
            re.compile("patient" + r"[-_ ]" + "outcome", re.IGNORECASE),
        ),
        (
            "out-of-scope decision phrase",
            re.compile("user" + r"[-_ ]" + "decision", re.IGNORECASE),
        ),
    ]


def _secret_patterns() -> list[tuple[str, re.Pattern[str]]]:
    return [
        (
            "private-key block",
            re.compile("-----BEGIN " + "PRIVATE" + " KEY-----"),
        ),
        (
            "private-key block",
            re.compile("-----BEGIN " + "OPENSSH" + " PRIVATE KEY-----"),
        ),
        ("AWS access identifier", re.compile("AK" + "IA" + r"[0-9A-Z]{16}")),
        (
            "GitHub access token",
            re.compile("gh" + r"[pousr]_[A-Za-z0-9]{30,}"),
        ),
        (
            "assigned credential-like value",
            re.compile(
                r"(?i)\b(?:api[_-]?key|secret|password|access[_-]?token)\b"
                r"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}"
            ),
        ),
        (
            "authorization bearer value",
            re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_./+=-]{12,}"),
        ),
    ]


def scan_release(root: Path) -> list[str]:
    errors: list[str] = []
    windows_absolute = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
    machine_absolute = re.compile(r"/(?:home|Users|mnt/[a-zA-Z])/")
    for path in release_files(root, include_manifest=True):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if path.is_symlink():
            errors.append(f"symlink is not allowed: {relative}")
            continue
        if not path.is_file():
            errors.append(f"non-regular release entry: {relative}")
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"file exceeds {MAX_FILE_BYTES} bytes: {relative}")
        path_tokens = {
            token
            for part in relative.parts
            for token in re.split(r"[-_.]+", part.casefold())
            if token
        }
        excluded = path_tokens & EXCLUDED_PATH_PARTS
        if excluded:
            errors.append(
                "excluded operational-history path component "
                f"{sorted(excluded)}: {relative}"
            )
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            "Makefile",
            ".gitattributes",
            ".gitignore",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"declared text file is not UTF-8: {relative}")
            continue
        for marker in MOJIBAKE_MARKERS:
            if marker in text:
                errors.append(f"mojibake marker {marker!r} found in {relative}")
        for label, pattern in _public_text_patterns():
            if pattern.search(text):
                errors.append(f"{label} found in {relative}")
        for label, pattern in _secret_patterns():
            if pattern.search(text):
                errors.append(f"{label} found in {relative}")
        if windows_absolute.search(text) or machine_absolute.search(text):
            errors.append(f"machine-specific absolute path found in {relative}")
    return errors


def _map_original_path(root: Path, original: str) -> Path | None:
    normalized = original.replace("\\", "/")
    generated_prefix = "research/generated/eval60-confirmatory-v1-20260720/"
    cve_prefix = "research/sources/raw/cve_program/"
    if normalized.startswith(generated_prefix):
        return root / "data" / "benchmark" / normalized.removeprefix(generated_prefix)
    if normalized.startswith(cve_prefix):
        return root / "data" / "sources" / "cve_program" / normalized.removeprefix(
            cve_prefix
        )
    if normalized == "research/scenarios/blueprint.yaml":
        return root / "data" / "sources" / "blueprint.yaml"
    if normalized == "knowledge/raw/known_exploited_vulnerabilities.json":
        return root / "data" / "sources" / "known_exploited_vulnerabilities.json"
    return None


def verify_reference_bindings(root: Path) -> list[str]:
    errors: list[str] = []
    evaluator = root / "data" / "benchmark" / "evaluator_only"
    scenario_manifest_path = evaluator / "scenario_manifest.json"
    source_manifest_path = evaluator / "reference_support" / "source_manifest.json"
    if not scenario_manifest_path.is_file() or not source_manifest_path.is_file():
        return ["scenario or source manifest is missing"]
    scenario_manifest = json.loads(scenario_manifest_path.read_text(encoding="utf-8"))
    for case in scenario_manifest.get("cases", []):
        for field, hash_field in (
            ("scenario_path", "scenario_sha256"),
            ("corpus_manifest_path", "corpus_manifest_sha256"),
        ):
            target = root / "data" / "benchmark" / case[field]
            if not target.is_file():
                errors.append(f"missing scenario-bound file: {target.relative_to(root)}")
            elif sha256_file(target) != case[hash_field]:
                errors.append(f"scenario-bound hash mismatch: {target.relative_to(root)}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    unresolved: list[str] = []
    for record in source_manifest.get("records", []):
        target = _map_original_path(root, record["snapshot_path"])
        if target is None:
            unresolved.append(record["snapshot_path"])
            continue
        if not target.is_file():
            errors.append(f"missing source-bound file: {target.relative_to(root)}")
        elif sha256_file(target) != record["snapshot_sha256"]:
            errors.append(f"source-bound hash mismatch: {target.relative_to(root)}")
    if unresolved:
        errors.append(f"unmapped source paths: {sorted(set(unresolved))[:3]}")
    return errors


def verify_cell_inventory(root: Path) -> list[str]:
    path = root / "data" / "derived" / "integrated_cell_scores.csv"
    if not path.is_file():
        return ["integrated cell score CSV is missing"]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    errors: list[str] = []
    if len(rows) != 3_000:
        errors.append(f"expected 3,000 score rows, found {len(rows)}")
        return errors
    keys = {(row["condition_id"], row["scenario_id"], row["run_index"]) for row in rows}
    if len(keys) != 3_000:
        errors.append("score keys are not unique")
    condition_counts = Counter(row["condition_id"] for row in rows)
    if len(condition_counts) != 10 or set(condition_counts.values()) != {300}:
        errors.append("score condition inventory is not ten by 300")
    if len({row["scenario_id"] for row in rows}) != 60:
        errors.append("score scenario inventory differs from 60")
    if len({row["family_id"] for row in rows}) != 30:
        errors.append("score family inventory differs from 30")
    if {row["run_index"] for row in rows} != {"1", "2", "3", "4", "5"}:
        errors.append("score repetition inventory differs from 1 through 5")
    if Counter(row["run_status"] for row in rows) != Counter(
        {"complete": 2_759, "failed": 236, "refusal": 5}
    ):
        errors.append("score terminal status totals differ")
    return errors


def verify_public_source_manifest(root: Path) -> list[str]:
    path = root / "data" / "sources" / "cve_program_source_manifest.json"
    if not path.is_file():
        return ["public CVE source manifest is missing"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    selection = root / manifest["selection_path"]
    if not selection.is_file():
        errors.append("public CVE source selection is missing")
    elif sha256_file(selection) != manifest["selection_sha256"]:
        errors.append("public CVE source selection hash differs")
    records = manifest.get("records", [])
    if len(records) != 18:
        errors.append(f"expected 18 public CVE source records, found {len(records)}")
    for record in records:
        target = root / record["artifact_path"]
        if not target.is_file():
            errors.append(f"public CVE source is missing: {record['artifact_path']}")
            continue
        if target.stat().st_size != record["bytes"]:
            errors.append(f"public CVE source size differs: {record['artifact_path']}")
        if sha256_file(target) != record["sha256"]:
            errors.append(f"public CVE source hash differs: {record['artifact_path']}")
    return errors


def _bound_release_file(root: Path, relative: object) -> Path | None:
    if not isinstance(relative, str) or "\\" in relative:
        return None
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        return None
    target = root / posix
    return target if target.is_file() else None


def verify_prediction_provenance(root: Path) -> list[str]:
    path = root / "metadata" / "prediction_provenance.json"
    if not path.is_file():
        return ["prediction provenance is missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"prediction provenance is invalid: {exc}"]

    errors: list[str] = []
    artifacts = payload.get("artifacts", {})
    bindings = (
        ("prediction_path", "prediction_sha256", "prediction_size_bytes"),
        ("prediction_schema_path", "prediction_schema_sha256", None),
        ("scorer_path", "scorer_sha256", None),
    )
    for path_key, hash_key, size_key in bindings:
        target = _bound_release_file(root, artifacts.get(path_key))
        if target is None:
            errors.append(f"prediction provenance path is missing or unsafe: {path_key}")
            continue
        if sha256_file(target) != artifacts.get(hash_key):
            errors.append(f"prediction provenance hash differs: {path_key}")
        if size_key is not None and target.stat().st_size != artifacts.get(size_key):
            errors.append(f"prediction provenance size differs: {path_key}")

    score_path = root / "data" / "derived" / "integrated_cell_scores.jsonl"
    if not score_path.is_file():
        errors.append("prediction provenance score matrix is missing")
    else:
        score_hash = sha256_file(score_path)
        reproduction = payload.get("score_reproduction", {})
        if reproduction.get("released_score_matrix_sha256") != score_hash:
            errors.append("prediction provenance released score hash differs")
        if reproduction.get("rescored_sha256") != score_hash:
            errors.append("prediction provenance rescored hash differs")
        if reproduction.get("status") != "PASS":
            errors.append("prediction provenance scoring status is not PASS")
        if reproduction.get("field_equal_rows") != 3_000:
            errors.append("prediction provenance field-equal row count differs")
        if reproduction.get("byte_equal") is not True:
            errors.append("prediction provenance byte-equality flag differs")

    projection = payload.get("projection", {})
    if (
        projection.get("row_count") != 3_000
        or projection.get("condition_count") != 10
        or projection.get("scenario_count") != 60
        or projection.get("repetitions") != [1, 2, 3, 4, 5]
    ):
        errors.append("prediction provenance matrix inventory differs")
    seed_schedule = payload.get("seed_schedule", {})
    if (
        seed_schedule.get("canonical_entries") != 1_500
        or seed_schedule.get("per_prediction_slots") != 5
        or seed_schedule.get("observed_seed_mismatches") != 0
        or seed_schedule.get("derived_or_imputed_seeds") != 0
    ):
        errors.append("prediction provenance seed audit differs")
    return errors


def verify_figure_manifest(root: Path) -> list[str]:
    figures = root / "figures"
    path = figures / "figure_manifest.json"
    if not path.is_file():
        return ["figure manifest is missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"figure manifest is invalid: {exc}"]

    expected: list[dict[str, Any]] = []
    for directory in ("masters", "source_data", "submission", "scripts"):
        for target in sorted((figures / directory).glob("*")):
            if target.is_file():
                expected.append(
                    {
                        "path": target.relative_to(figures).as_posix(),
                        "size_bytes": target.stat().st_size,
                        "sha256": sha256_file(target),
                    }
                )
    errors: list[str] = []
    if payload.get("files") != expected:
        errors.append("figure manifest inventory or hashes differ")
    if payload.get("figure_count") != 3:
        errors.append("figure manifest figure count differs")
    return errors


def verify_evaluation_matrix(root: Path) -> list[str]:
    matrix_path = root / "configs" / "evaluation_matrix.jsonl"
    score_path = root / "data" / "derived" / "integrated_cell_scores.csv"
    if not matrix_path.is_file() or not score_path.is_file():
        return ["evaluation matrix or integrated score CSV is missing"]
    try:
        records = [
            json.loads(line)
            for line in matrix_path.read_text(encoding="utf-8").splitlines()
            if line
        ]
    except (OSError, json.JSONDecodeError) as exc:
        return [f"evaluation matrix is invalid: {exc}"]
    with score_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(
        key=lambda row: (
            row["condition_id"],
            int(row["run_index"]),
            row["blind_case_id"],
        )
    )
    expected = [
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
        for ordinal, row in enumerate(rows)
    ]
    if len(records) != 3_000:
        return [f"expected 3,000 evaluation matrix rows, found {len(records)}"]
    if records != expected:
        return ["evaluation matrix differs from the integrated score matrix"]
    return []


def verify_third_party_notices(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in (Path("THIRD_PARTY_NOTICES.md"), Path("data/sources/NOTICE.md")):
        path = root / relative
        if not path.is_file():
            errors.append(f"third-party notice is missing: {relative.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in SOURCE_NOTICE_MARKERS:
            if marker not in text:
                errors.append(
                    f"third-party notice lacks required upstream marker "
                    f"{marker!r}: {relative.as_posix()}"
                )
    return errors


def publication_license_errors(root: Path) -> list[str]:
    errors: list[str] = []
    code_license = root / "LICENSE"
    if not code_license.is_file() or code_license.stat().st_size < 100:
        errors.append("author-approved LICENSE is required for public distribution")

    data_license = root / "LICENSE-DATA"
    if not data_license.is_file() or data_license.stat().st_size < 100:
        errors.append("author-approved LICENSE-DATA is required for public distribution")
    else:
        text = data_license.read_text(encoding="utf-8")
        for marker in DATA_LICENSE_MARKERS:
            if marker not in text:
                errors.append(
                    f"author-approved LICENSE-DATA lacks required scope or upstream "
                    f"marker: {marker!r}"
                )
    return errors


def verify_all(root: Path, *, publication: bool = False) -> list[str]:
    errors = []
    errors.extend(scan_release(root))
    errors.extend(verify_cell_inventory(root))
    errors.extend(verify_public_source_manifest(root))
    errors.extend(verify_reference_bindings(root))
    errors.extend(verify_prediction_provenance(root))
    errors.extend(verify_figure_manifest(root))
    errors.extend(verify_evaluation_matrix(root))
    errors.extend(verify_third_party_notices(root))
    errors.extend(verify_manifest(root))
    if publication:
        errors.extend(publication_license_errors(root))
    return errors


__all__ = [
    "manifest_entries",
    "publication_license_errors",
    "release_files",
    "scan_release",
    "sha256_file",
    "verify_all",
    "verify_cell_inventory",
    "verify_evaluation_matrix",
    "verify_figure_manifest",
    "verify_manifest",
    "verify_prediction_provenance",
    "verify_public_source_manifest",
    "verify_reference_bindings",
    "verify_third_party_notices",
    "write_manifest",
]
