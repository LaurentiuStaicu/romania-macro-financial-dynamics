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
        raise RuntimeError("A1 audit is not the expected 72-cell F2M stock/flow audit")
    if a1.get("total_F2_materialization_allowed") is not False:
        raise RuntimeError("A1 must prohibit total-F2 materialization")
    if a2.get("promotion_status") != "EXACT_COMPLEMENT_DERIVATION_ELIGIBLE_FOR_LATER_MATERIALIZATION":
        raise RuntimeError("A2 did not pass the exact-complement promotion gate")
    if a2.get("all_required_identity_controls_pass") is not True:
        raise RuntimeError("A2 required identity controls do not all pass")
    for item in a2["measure_results"]:
        required = (
            item["independent_domestic_partition_status"],
            item["resident_holder_W0_vs_total_W0_status"],
            item["holder_complements_vs_W1_status"],
        )
        if required != ("PASS", "PASS", "PASS"):
            raise RuntimeError(f"A2 identity control failure for {item['measure']}")
        if item["direct_area_partition_status"] not in {"PASS", "CONTROL_UNAVAILABLE"}:
            raise RuntimeError(f"A2 direct area control failed for {item['measure']}")

    by_measure_holder = {
        (x["measure"], x["holder"]): x
        for x in a2["complement_candidates"]
    }
    for rec in a1["aggregate_reconciliation"]:
        if rec["kind"] != "holder_total" or rec["sector"] == "X":
            continue
        candidate = by_measure_holder[(rec["measure"], rec["sector"])]
        expected = float(rec["official_aggregate_million_RON"]) - float(rec["bilateral_sum_million_RON"])
        actual = candidate["candidate_value_million_RON"]
        if actual is None or not math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=1e-9):
            raise RuntimeError(f"External complement mismatch for {rec['measure']} {rec['sector']}")


def classify_a1_cell(cell: dict) -> str:
    status = cell["status"]
    if status in {"STRUCTURAL_NOT_APPLICABLE_ESA", "OUTSIDE_BOUNDARY_CANDIDATE_NOT_APPLICABLE"}:
        return "NOT_APPLICABLE"
    if status == "UNRESOLVED_SOURCE_COVERAGE":
        return "EXTERNAL_COMPLEMENT"
    if status != "OBSERVABLE_OR_EXACT_DERIVATION":
        raise RuntimeError(f"Unknown A1 cell status: {status}")
    if cell["measure"] == "flow":
        return "DERIVED"
    return "OBSERVED" if len(cell.get("terms", [])) == 1 else "DERIVED"


def build_component(source_manifest: dict, a1: dict, a2: dict) -> tuple[dict, dict]:
    complements = {
        (x["measure"], x["holder"]): x
        for x in a2["complement_candidates"]
    }
    holder_controls = {
        (x["measure"], x["sector"]): x
        for x in a1["aggregate_reconciliation"]
        if x["kind"] == "holder_total"
    }

    matrices: dict[str, list[dict]] = {"stock": [], "flow": []}
    for measure in ("stock", "flow"):
        selected = [x for x in a1["cells"] if x["measure"] == measure]
        index = {(x["holder"], x["issuer"]): x for x in selected}
        if set(index) != {(h, i) for h in SECTORS for i in SECTORS}:
            raise RuntimeError(f"A1 {measure} matrix does not cover the canonical 6x6 boundary")

        for holder in SECTORS:
            for issuer in SECTORS:
                raw = index[(holder, issuer)]
                classification = classify_a1_cell(raw)
                out: dict = {
                    "holder": holder,
                    "issuer": issuer,
                    "status": classification,
                    "value": None,
                    "unit": "million_RON",
                }
                if classification == "NOT_APPLICABLE":
                    out["reason"] = (
                        "ESA2010_DEPOSIT_NON_ISSUER"
                        if issuer in {"H", "C"}
                        else "OUTSIDE_ROMANIAN_NATIONAL_ACCOUNTS_BOUNDARY"
                    )
                elif classification == "EXTERNAL_COMPLEMENT":
                    if holder == "X" or issuer != "X":
                        raise RuntimeError("Unexpected external-complement cell")
                    candidate = complements[(measure, holder)]
                    if candidate["candidate_value_million_RON"] is None:
                        raise RuntimeError(f"Missing complement value for {measure} {holder}->X")
                    out["status"] = "DERIVED"
                    out["value"] = round(float(candidate["candidate_value_million_RON"]), 2)
                    control = holder_controls[(measure, holder)]
                    out["derivation"] = {
