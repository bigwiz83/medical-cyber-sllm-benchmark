from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.integrity import (  # noqa: E402
    manifest_entries,
    publication_license_errors,
    verify_all,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify public reproducibility release contents")
    parser.add_argument(
        "--publication",
        action="store_true",
        help="also require author-approved code and data licenses",
    )
    args = parser.parse_args()
    errors = verify_all(ROOT, publication=args.publication)
    report = {
        "status": "PASS" if not errors else "FAIL",
        "publication_mode": args.publication,
        "content_file_count": len(manifest_entries(ROOT)),
        "content_size_bytes": sum(item["size_bytes"] for item in manifest_entries(ROOT)),
        "license_gate": (
            "PASS" if not publication_license_errors(ROOT) else "PENDING_AUTHOR_APPROVAL"
        ),
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

