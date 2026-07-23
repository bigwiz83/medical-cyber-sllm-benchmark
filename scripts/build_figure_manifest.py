from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
TARGET = FIGURES / "figure_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    files = []
    for directory in ("masters", "source_data", "submission", "scripts"):
        for path in sorted((FIGURES / directory).glob("*")):
            if path.is_file():
                files.append(
                    {
                        "path": path.relative_to(FIGURES).as_posix(),
                        "size_bytes": path.stat().st_size,
                        "sha256": sha256(path),
                    }
                )
    payload = {
        "schema_version": "public-figure-manifest-1.0.0",
        "figure_count": 3,
        "typeface_policy": "Arial, Helvetica, sans-serif",
        "files": files,
    }
    TARGET.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(files)} figure assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
