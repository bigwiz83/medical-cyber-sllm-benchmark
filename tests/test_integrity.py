from __future__ import annotations

from pathlib import Path

from medcyber_benchmark.integrity import (
    publication_license_errors,
    scan_release,
    verify_cell_inventory,
    verify_evaluation_matrix,
    verify_figure_manifest,
    verify_manifest,
    verify_prediction_provenance,
    verify_public_source_manifest,
    verify_reference_bindings,
    verify_third_party_notices,
)

ROOT = Path(__file__).resolve().parents[1]


def test_public_content_gates() -> None:
    assert scan_release(ROOT) == []
    assert verify_cell_inventory(ROOT) == []
    assert verify_public_source_manifest(ROOT) == []
    assert verify_reference_bindings(ROOT) == []
    assert verify_prediction_provenance(ROOT) == []
    assert verify_figure_manifest(ROOT) == []
    assert verify_evaluation_matrix(ROOT) == []
    assert verify_third_party_notices(ROOT) == []
    assert verify_manifest(ROOT) == []


def test_publication_license_gate_is_explicit(tmp_path: Path) -> None:
    assert len(publication_license_errors(tmp_path)) == 2
    (tmp_path / "LICENSE").write_text(
        "author-approved code license text\n" * 10, encoding="utf-8"
    )
    (tmp_path / "LICENSE-DATA").write_text(
        "\n".join(
            (
                "Creative Commons Attribution 4.0 International",
                "study-authored synthetic and derived material",
                "https://www.cve.org/legal/termsofuse",
                "https://www.cisa.gov/sites/default/files/licenses/kev/license.txt",
                "The MITRE Corporation",
                "CVE Usage",
                "CC0 1.0",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    assert publication_license_errors(tmp_path) == []


def test_third_party_notices_are_utf8_without_mojibake() -> None:
    expected = "Copyright © 1999–2026, The MITRE Corporation."
    for relative in ("THIRD_PARTY_NOTICES.md", "data/sources/NOTICE.md"):
        raw = (ROOT / relative).read_bytes()
        text = raw.decode("utf-8")
        assert expected in " ".join(text.split())
        assert chr(0xFFFD) not in text
        assert chr(0xC9E4) not in text
        assert "?" * 2 + "026" not in text
