from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from medcyber_benchmark.integrity import manifest_entries, write_manifest  # noqa: E402


def main() -> int:
    target = write_manifest(ROOT)
    entries = manifest_entries(ROOT)
    print(
        f"WROTE: {target.relative_to(ROOT)} ({len(entries)} files, "
        f"{sum(item['size_bytes'] for item in entries)} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
