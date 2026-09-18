from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import zipfile
from io import BytesIO
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VINTAGE = ROOT / "data" / "source_vintages" / "accounting-f2m-2025-vintage-2026-09-18"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
TOL = 0.1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_bytes(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


def load_vintage(vintage: Path) -> tuple[dict, zipfile.ZipFile, dict, dict]:
    source_manifest = json.loads((vintage / "source_manifest.json").read_text(encoding="utf-8"))
    archive_path = vintage / source_manifest["archive"]
    encoded = "".join(archive_path.read_text(encoding="ascii").split())
    archive_bytes = base64.b64decode(encoded, validate=True)
    actual = sha256_bytes(archive_bytes)
    expected = source_manifest["decoded_archive_sha256"]
    if actual != expected:
        raise RuntimeError(f"F2M source artifact digest mismatch: {actual} != {expected}")

    zf = zipfile.ZipFile(BytesIO(archive_bytes))
    members = set(zf.namelist())
    a1_path = source_manifest["archive_contains"]["phase_a1_report"]
    a2_path = source_manifest["archive_contains"]["phase_a2_report"]
    if a1_path not in members or a2_path not in members:
        raise RuntimeError("Retained F2M artifact is missing an audit report")
    a1 = load_json_bytes(zf.read(a1_path))
    a2 = load_json_bytes(zf.read(a2_path))
    return source_manifest, zf, a1, a2


def raw_name_for_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16] + ".raw"


def verify_raw_coverage(source_manifest: dict, zf: zipfile.ZipFile, a1: dict, a2: dict) -> dict:
    members = set(zf.namelist())
    a1_prefix = source_manifest["archive_contains"]["phase_a1_raw_directory"]
    a2_prefix = source_manifest["archive_contains"]["phase_a2_raw_directory"]

    keys: set[str] = set()
    for cell in a1["cells"]:
        for term in cell.get("terms", []):
            keys.add(term["key"])
    for item in a1["aggregate_reconciliation"]:
        for term in item.get("terms", []):
            keys.add(term["key"])

    missing = []
    for key in sorted(keys):
        inner = a1_prefix + raw_name_for_key(key)
        if inner not in members:
            missing.append({"key": key, "expected_member": inner})
    if missing:
        raise RuntimeError(f"F2M A1 retained raw coverage incomplete: {missing[:3]}")

    a2_verified = 0
    for series in a2["aggregate_series"]:
        inner = str(PurePosixPath(a2_prefix) / PurePosixPath(series["raw_path"]).name)
        if inner not in members:
            raise RuntimeError(f"Missing A2 raw payload: {inner}")
        actual = sha256_bytes(zf.read(inner))
        if actual != series["raw_sha256"]:
            raise RuntimeError(f"A2 raw SHA mismatch for {series['key']}")
        a2_verified += 1

    return {
        "phase_a1_distinct_series_keys_with_retained_raw": len(keys),
        "phase_a2_raw_payloads_sha256_verified": a2_verified,
    }


def verify_audits(a1: dict, a2: dict) -> None:
    if a1.get("instrument") != "F2M" or len(a1.get("cells", [])) != 72:
