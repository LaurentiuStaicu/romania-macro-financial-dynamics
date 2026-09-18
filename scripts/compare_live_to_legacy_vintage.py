from __future__ import annotations

import json
import sys
from pathlib import Path


def by_name(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(item["name"]): item
        for item in manifest.get("attempts", [])
    }


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: compare_live_to_legacy_vintage.py "
            "LIVE_MANIFEST LEGACY_MANIFEST OUTPUT_JSON"
        )

    live_path = Path(sys.argv[1])
    legacy_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    live = json.loads(live_path.read_text(encoding="utf-8"))
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    live_sources = by_name(live)
    legacy_sources = by_name(legacy)

    names = sorted(set(live_sources) | set(legacy_sources))
    comparisons = []
    all_match = True
    for name in names:
        current = live_sources.get(name)
        historical = legacy_sources.get(name)
        same = bool(
            current
            and historical
            and current.get("sha256") == historical.get("sha256")
        )
        all_match = all_match and same
        comparisons.append(
            {
                "name": name,
                "legacy_sha256": historical.get("sha256") if historical else None,
                "live_sha256": current.get("sha256") if current else None,
                "exact_sha256_match": same,
            }
        )

    result = {
        "legacy_manifest": str(legacy_path),
        "live_manifest": str(live_path),
        "all_raw_payloads_exact_sha256_match": all_match,
        "comparisons": comparisons,
        "interpretation": (
            "MATCH permits the live raw bytes to serve as byte-identical materialization "
            "of the historical payload hashes. MISMATCH means the historical vintage "
            "must remain HASH_ONLY_LEGACY and the live fetch is a new vintage."
        ),
    }
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
