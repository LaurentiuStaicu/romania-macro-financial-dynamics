from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "source_vintages" / "accounting-f3-2025-vintage-2026-09-18"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest_path = SNAPSHOT / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest["snapshot_id"] != "accounting-f3-2025-vintage-2026-09-18":
        raise RuntimeError("Unexpected F3 snapshot identity")
    if manifest["rules"]["raw_responses_retained"] is not True:
        raise RuntimeError("Snapshot does not claim retained raw responses")
    if manifest["rules"]["network_required_for_reproduction"] is not False:
        raise RuntimeError("F3 snapshot reproduction must be offline")

    listed = {}
    for item in manifest["files"]:
        relative = item["path"]
        if relative in listed:
            raise RuntimeError(f"Duplicate snapshot manifest path: {relative}")
        path = SNAPSHOT / relative
        if not path.is_file():
            raise RuntimeError(f"Missing snapshot file: {relative}")
        observed_bytes = path.stat().st_size
        observed_sha = sha256_file(path)
        if observed_bytes != item["bytes"]:
            raise RuntimeError(
                f"Snapshot byte-count mismatch for {relative}: "
                f"{observed_bytes} != {item['bytes']}"
            )
        if observed_sha != item["sha256"]:
            raise RuntimeError(
                f"Snapshot SHA-256 mismatch for {relative}: "
                f"{observed_sha} != {item['sha256']}"
            )
        listed[relative] = item

    actual = {
        str(path.relative_to(SNAPSHOT))
        for path in SNAPSHOT.rglob("*")
        if path.is_file() and path.name != "snapshot_manifest.json"
    }
    if actual != set(listed):
        missing_from_manifest = sorted(actual - set(listed))
        missing_from_snapshot = sorted(set(listed) - actual)
        raise RuntimeError(
            "Snapshot file-set mismatch; "
            f"unlisted={missing_from_manifest}; missing={missing_from_snapshot}"
        )

    series_manifest = json.loads(
        (SNAPSHOT / "qsa_f3_series_manifest.json").read_text(encoding="utf-8")
    )
    series = series_manifest["series"]
    if len(series) != 144:
        raise RuntimeError(f"Expected 144 audited QSA series, found {len(series)}")

    available = 0
    unavailable = 0
    for item in series:
        raw_path = item.get("raw_path")
        if not raw_path:
            raise RuntimeError(f"Audited series lacks retained raw path: {item['key']}")
        path = SNAPSHOT / raw_path
        if not path.is_file():
            raise RuntimeError(f"Audited raw response missing: {raw_path}")
        if sha256_file(path) != item["raw_sha256"]:
            raise RuntimeError(f"Raw series hash mismatch: {item['key']}")
        if item["status"] == "AVAILABLE":
            if item.get("unit_values") != ["XDC"]:
                raise RuntimeError(f"Unexpected unit for {item['key']}: {item.get('unit_values')}")
            if item.get("unit_mult_values") != ["6"]:
                raise RuntimeError(
                    f"Unexpected unit multiplier for {item['key']}: "
                    f"{item.get('unit_mult_values')}"
                )
            if item.get("decimal_values") != ["2"]:
                raise RuntimeError(
                    f"Unexpected published precision for {item['key']}: "
                    f"{item.get('decimal_values')}"
                )
            available += 1
        elif item["status"] == "HTTP_ERROR":
            unavailable += 1
        else:
            raise RuntimeError(
                f"Unexpected series status {item['status']} for {item['key']}"
            )

    if (available, unavailable) != (94, 50):
        raise RuntimeError(
            f"Unexpected QSA coverage counts: available={available}, unavailable={unavailable}"
        )

    audit = json.loads(
        (SNAPSHOT / "qsa_f3_coverage_audit.json").read_text(encoding="utf-8")
    )
    if audit["series_status_counts"] != {"AVAILABLE": 94, "HTTP_ERROR": 50}:
        raise RuntimeError("Audit series-status counts drifted")
    if audit["aggregate_reconciliation_status_counts"] != {"PASS": 20}:
        raise RuntimeError("Not all aggregate F3 reconciliation controls pass")
    if audit["maturity_reconciliation_status_counts"] != {"PASS": 2}:
        raise RuntimeError("Not all F3 maturity controls pass")

    cells = audit["cells"]
    if len(cells) != 72:
        raise RuntimeError(f"Expected 72 F3 stock/flow logical cells, found {len(cells)}")

    unresolved = [
        item
        for item in cells
        if item["holder"] != "X"
        or item["issuer"] != "X"
        if item["canonical_value_million_RON"] is None
    ]
    if unresolved:
        raise RuntimeError(f"Unexpected unresolved in-boundary F3 cells: {unresolved}")

    print(
        "F3 source vintage verified: 144 raw responses, "
        "94 available series, 50 explicit HTTP errors, "
        "20 aggregate controls PASS, 2 maturity controls PASS."
    )


if __name__ == "__main__":
    main()
