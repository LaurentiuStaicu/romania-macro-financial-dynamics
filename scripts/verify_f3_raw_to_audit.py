from __future__ import annotations

import csv
import hashlib
import importlib
import io
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "data"
    / "source_vintages"
    / "accounting-f3-2025-vintage-2026-09-18"
)
SNAPSHOT_MANIFEST = SNAPSHOT / "snapshot_manifest.json"
SERIES_MANIFEST = SNAPSHOT / "qsa_f3_series_manifest.json"
AUDIT_JSON = SNAPSHOT / "qsa_f3_coverage_audit.json"
CELL_SUMMARY = SNAPSHOT / "qsa_f3_cell_summary.csv"
AUDIT_SCRIPT = ROOT / "scripts" / "audit_qsa_accounting_coverage.py"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_available_csv(payload: bytes) -> list[dict[str, object]]:
    text = payload.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    parsed: list[dict[str, object]] = []

    for row in rows:
        period = row.get("TIME_PERIOD")
        value = row.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue

        try:
            numeric = float(value)
        except ValueError:
            continue

        decimals_raw = row.get("DECIMALS")
        try:
            decimals = (
                int(decimals_raw)
                if decimals_raw not in (None, "")
                else None
            )
        except ValueError:
            decimals = None

        parsed.append(
            {
                "period": period,
                "value_raw": numeric,
                "value_published_precision": (
                    round(numeric, decimals)
                    if decimals is not None
                    else numeric
                ),
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "obs_status": row.get("OBS_STATUS"),
                "decimals": decimals,
            }
        )

    return parsed


def rebuild_series_entry(
    retained: dict[str, object],
) -> dict[str, object]:
    raw_path = SNAPSHOT / str(retained["raw_path"])
    if not raw_path.is_file():
        raise RuntimeError(f"Missing retained raw response: {raw_path}")

    payload = raw_path.read_bytes()
    observed_sha = sha256_bytes(payload)
    observed_bytes = len(payload)

    if observed_sha != retained["raw_sha256"]:
        raise RuntimeError(
            f"Raw SHA-256 mismatch for {retained['key']}: "
            f"{observed_sha} != {retained['raw_sha256']}"
        )
    if observed_bytes != retained["raw_bytes"]:
        raise RuntimeError(
            f"Raw byte-count mismatch for {retained['key']}: "
            f"{observed_bytes} != {retained['raw_bytes']}"
        )

    rebuilt: dict[str, object] = {
        "key": retained["key"],
        "url": retained["url"],
        "http_status": retained["http_status"],
        "raw_path": retained["raw_path"],
        "raw_bytes": observed_bytes,
        "raw_sha256": observed_sha,
        "content_type": retained.get("content_type"),
        "last_modified": retained.get("last_modified"),
        "etag": retained.get("etag"),
        "rows": [],
    }

    if int(retained["http_status"]) != 200:
        rebuilt["status"] = "HTTP_ERROR"
        return rebuilt

    parsed = parse_available_csv(payload)
    rebuilt["rows"] = parsed
    rebuilt["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    rebuilt["unit_values"] = sorted(
        {str(row["unit"]) for row in parsed}
    )
    rebuilt["unit_mult_values"] = sorted(
        {str(row["unit_mult"]) for row in parsed}
    )
    rebuilt["decimal_values"] = sorted(
        {
            str(row["decimals"])
            for row in parsed
            if row["decimals"] is not None
        }
    )
    return rebuilt


def assert_semantic_equal(
    label: str,
    retained: object,
    rebuilt: object,
) -> None:
    if retained != rebuilt:
        raise RuntimeError(f"{label} does not reproduce semantically from raw bytes")


def main() -> None:
    snapshot_manifest = json.loads(
        SNAPSHOT_MANIFEST.read_text(encoding="utf-8")
    )
    retained_series_manifest = json.loads(
        SERIES_MANIFEST.read_text(encoding="utf-8")
    )
    retained_audit = json.loads(
        AUDIT_JSON.read_text(encoding="utf-8")
    )

    recorded_script_sha = snapshot_manifest["audit_script_sha256"]
    current_script_sha = sha256_file(AUDIT_SCRIPT)
    if current_script_sha != recorded_script_sha:
        raise RuntimeError(
            "The retained F3 snapshot was produced by a different audit-script "
            f"version: current={current_script_sha}, "
            f"recorded={recorded_script_sha}. "
            "Do not silently reinterpret the vintage; retain the capture script "
            "or explicitly version the parser."
        )

    rebuilt_series = [
        rebuild_series_entry(item)
        for item in retained_series_manifest["series"]
    ]
    rebuilt_series_manifest = {"series": rebuilt_series}
    assert_semantic_equal(
        "QSA F3 series manifest",
        retained_series_manifest,
        rebuilt_series_manifest,
    )

    rebuilt_by_key = {
        str(item["key"]): item
        for item in rebuilt_series
    }
    if len(rebuilt_by_key) != 144:
        raise RuntimeError(
            f"Expected 144 unique retained QSA series, found {len(rebuilt_by_key)}"
        )

    audit_module = importlib.import_module(
        "scripts.audit_qsa_accounting_coverage"
    )

    original_fetch = audit_module.fetch_series
    original_out = audit_module.OUT

    with tempfile.TemporaryDirectory() as directory:
        regenerated_dir = Path(directory)

        def offline_fetch(key: str) -> dict[str, object]:
            try:
                return rebuilt_by_key[key]
            except KeyError as exc:
                raise RuntimeError(
                    f"Audit requested a QSA key absent from retained vintage: {key}"
                ) from exc

        audit_module.fetch_series = offline_fetch
        audit_module.OUT = regenerated_dir
        try:
            audit_module.main()
        finally:
            audit_module.fetch_series = original_fetch
            audit_module.OUT = original_out

        regenerated_audit = json.loads(
            (regenerated_dir / "qsa_f3_coverage_audit.json").read_text(
                encoding="utf-8"
            )
        )
        regenerated_series_manifest = json.loads(
            (regenerated_dir / "qsa_f3_series_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        regenerated_summary = (
            regenerated_dir / "qsa_f3_cell_summary.csv"
        ).read_bytes()

    assert_semantic_equal(
        "F3 coverage/reconciliation audit",
        retained_audit,
        regenerated_audit,
    )
    assert_semantic_equal(
        "regenerated QSA series manifest",
        retained_series_manifest,
        regenerated_series_manifest,
    )

    retained_summary = CELL_SUMMARY.read_bytes()
    if regenerated_summary != retained_summary:
        raise RuntimeError(
            "F3 cell-summary CSV does not reproduce byte-for-byte from retained raw data"
        )

    available = sum(
        1 for item in rebuilt_series if item["status"] == "AVAILABLE"
    )
    http_errors = sum(
        1 for item in rebuilt_series if item["status"] == "HTTP_ERROR"
    )
    print(
        "F3 raw-to-audit chain verified fully offline: "
        f"144 retained raw responses -> {available} available series + "
        f"{http_errors} explicit HTTP-error responses -> "
        "series manifest -> coverage/reconciliation audit -> cell summary."
    )


if __name__ == "__main__":
    main()
