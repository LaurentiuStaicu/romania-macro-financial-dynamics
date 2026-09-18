from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VINTAGE = (
    ROOT / "data" / "source_vintages"
    / "accounting-f4-partial-2025-vintage-2026-09-18"
)
SECTORS = ("H", "C", "F", "G", "X", "BNR")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_vintage(vintage: Path):
    source = json.loads((vintage / "source_manifest.json").read_text(encoding="utf-8"))
    encoded = "".join((vintage / source["archive"]).read_text(encoding="ascii").split())
    archive = base64.b64decode(encoded, validate=True)
    digest = sha256(archive)
    if digest != source["decoded_archive_sha256"]:
        raise RuntimeError(f"F4 source-vintage digest mismatch: {digest}")
    zf = zipfile.ZipFile(BytesIO(archive))
    names = set(zf.namelist())
    a_path = source["archive_contains"]["phase_A_report"]
    b_path = source["archive_contains"]["phase_B_report"]
    if a_path not in names or b_path not in names:
        raise RuntimeError("F4 retained artifact is missing Phase A or Phase B report")
    a_raw = [
        n for n in names
        if n.startswith(source["archive_contains"]["phase_A_raw_directory"])
        and n.endswith(".raw")
    ]
    b_raw = [
        n for n in names
        if n.startswith(source["archive_contains"]["phase_B_raw_directory"])
        and n.endswith(".raw")
    ]
    if len(a_raw) != source["archive_contains"]["phase_A_raw_response_count"]:
        raise RuntimeError(f"Unexpected Phase A raw count: {len(a_raw)}")
    if len(b_raw) != source["archive_contains"]["phase_B_raw_response_count"]:
        raise RuntimeError(f"Unexpected Phase B raw count: {len(b_raw)}")
    phase_a = json.loads(zf.read(a_path).decode("utf-8"))
    phase_b = json.loads(zf.read(b_path).decode("utf-8"))
    return source, zf, phase_a, phase_b, {
        "decoded_archive_sha256": digest,
        "phase_A_raw_responses": len(a_raw),
        "phase_B_raw_responses": len(b_raw),
    }


def direct_provenance(cell: dict) -> dict:
    orientation_name = cell.get("selected_orientation")
    maturity_derivation = cell.get("derivation")
    orientation = cell.get("orientations", {}).get(orientation_name, {})
    maturity_keys = (
        ("T",) if maturity_derivation == "DIRECT_T"
        else ("S", "L") if maturity_derivation == "EXACT_S_PLUS_L"
        else ()
    )
    terms = []
    for maturity in maturity_keys:
        for term in orientation.get("terms", {}).get(maturity, {}).get("terms", []):
            terms.append({
                "maturity": maturity,
                "coefficient": term["coefficient"],
                "qsa_key": term["key"],
                "values": term.get("values"),
            })
    return {
        "phase_A_selected_orientation": orientation_name,
        "phase_A_maturity_derivation": maturity_derivation,
        "source_terms": terms,
    }


def build(phase_a: dict, phase_b: dict, source: dict, provenance: dict):
    a_cells = {
        (c["measure"], c["holder"], c["issuer"]): c
        for c in phase_a["cells"]
    }
    b_derivations = {
        (measure, item["cell"]): item
        for measure, items in phase_b["explicit_derivation_candidates"].items()
        for item in items
        if item.get("rank_uniqueness_confirmed")
    }

    unique = {
        "stock": set(
            phase_b["analyses"]["stock"][
                "identification_before_structural_zero"
            ]["unique_cells"]
        ),
        "flow": set(
            phase_b["analyses"]["flow"][
                "identification_before_structural_zero"
            ]["unique_cells"]
        ),
    }
    if len(unique["stock"]) != 15 or len(unique["flow"]) != 15:
        raise RuntimeError("Unexpected unconditional Phase B unique-cell topology")

    matrices = {}
    counts = {}
    for measure in ("stock", "flow"):
        cells = []
        ctr = Counter()
        for holder in SECTORS:
            for issuer in SECTORS:
                label = f"{holder}→{issuer}"
                if holder == "X" and issuer == "X":
                    out = {
                        "holder": holder,
                        "issuer": issuer,
                        "status": "NOT_APPLICABLE",
                        "value": None,
                        "unit": "million_RON",
                        "reason": "outside_Romanian_national_accounts_boundary",
                    }
                elif label not in unique[measure]:
                    out = {
                        "holder": holder,
                        "issuer": issuer,
                        "status": "UNRESOLVED",
                        "value": None,
                        "unit": "million_RON",
                        "reason": "not_unconditional_rank_unique_in_F4_Phase_B",
                    }
                else:
                    a_cell = a_cells[(measure, holder, issuer)]
                    if a_cell.get("value_million_RON") is not None:
                        value = float(a_cell["value_million_RON"])
                        status = (
                            "OBSERVED"
                            if measure == "stock"
                            and a_cell.get("derivation") == "DIRECT_T"
                            else "DERIVED"
                        )
                        out = {
                            "holder": holder,
                            "issuer": issuer,
                            "status": status,
                            "value": round(value, 2),
                            "unit": "million_RON",
                            "derivation": (
                                "direct_QSA_2025Q4_all_maturity_position"
                                if status == "OBSERVED"
                                else "exact_Phase_A_temporal_or_maturity_derivation"
                            ),
                            "provenance": direct_provenance(a_cell),
                        }
                    else:
                        item = b_derivations.get((measure, label))
                        if item is None:
                            raise RuntimeError(
                                f"Unique cell lacks direct or Phase B derivation: {measure} {label}"
                            )
                        out = {
                            "holder": holder,
                            "issuer": issuer,
                            "status": "DERIVED",
                            "value": round(float(item["value_million_RON"]), 2),
                            "unit": "million_RON",
                            "derivation": item["method"],
                            "phase_B_rank_uniqueness_confirmed": True,
                        }
                cells.append(out)
                ctr[out["status"]] += 1
        matrices[measure] = cells
        counts[measure] = dict(sorted(ctr.items()))

    if sum(counts["stock"].get(k, 0) for k in ("OBSERVED", "DERIVED")) != 15:
        raise RuntimeError(f"Unexpected stock materialized count: {counts['stock']}")
    if counts["stock"].get("UNRESOLVED") != 20 or counts["stock"].get("NOT_APPLICABLE") != 1:
        raise RuntimeError(f"Unexpected stock unresolved topology: {counts['stock']}")
    if counts["flow"] != {"DERIVED": 15, "NOT_APPLICABLE": 1, "UNRESOLVED": 20}:
        raise RuntimeError(f"Unexpected flow counts: {counts['flow']}")

    conditional_stock = set(
        phase_b["analyses"]["stock"][
            "identification_with_stock_BNR_zero"
        ]["unique_cells"]
    )
    conditional_only = sorted(conditional_stock - unique["stock"])
    if len(conditional_only) != 10:
        raise RuntimeError("Expected ten conditional-only stock cells")

    component = {
        "artifact_version": "0.1",
        "instrument": "F4",
        "scope": "partial_unconditional_rank_unique_core",
        "complete_F4_matrix": False,
        "canonical_benchmark_changed": False,
        "benchmark_stock_period": "2025-Q4",
        "benchmark_flow_period": "2025-Q1..2025-Q4",
        "source_vintage": (
            "data/source_vintages/"
            "accounting-f4-partial-2025-vintage-2026-09-18"
        ),
        "source_vintage_sha256": provenance["decoded_archive_sha256"],
        "matrices": matrices,
        "conditional_stock_cells_not_promoted": conditional_only,
        "remaining_stock_rank_nonunique_cells":
            phase_b["analyses"]["stock"][
                "identification_with_stock_BNR_zero"
            ]["nonunique_cells"],
        "remaining_flow_rank_nonunique_cells":
            phase_b["analyses"]["flow"][
                "identification_before_structural_zero"
            ]["nonunique_cells"],
    }

    manifest = {
        "materialization_version": "0.1",
        "instrument": "F4",
        "scope": "partial_unconditional_rank_unique_core",
        "component_path": "model/accounting/f4_partial_2025.json",
        "source_workflow_run_id": source["workflow_run_id"],
        "source_workflow_artifact_id": source["workflow_artifact_id"],
        "source_workflow_artifact_sha256": source["decoded_archive_sha256"],
        "provenance_verification": provenance,
        "counts": counts,
        "rank_boundary": {
            "stock_unconditional":
                phase_b["analyses"]["stock"][
                    "identification_before_structural_zero"
                ],
            "flow_unconditional":
                phase_b["analyses"]["flow"][
                    "identification_before_structural_zero"
                ],
            "stock_conditional_BNR_zero":
                phase_b["analyses"]["stock"][
                    "identification_with_stock_BNR_zero"
                ],
        },
        "conditional_stock_cells_promoted": False,
        "conditional_stock_cells_not_promoted": conditional_only,
        "BNR_asset_counterpart_allocation_performed": False,
        "canonical_benchmark_2025_changed": False,
        "behavioural_closure_changed": False,
        "status": "PARTIAL_F4_UNCONDITIONAL_CORE_MATERIALIZED_FULL_F4_INCOMPLETE",
    }
    return component, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", type=Path, default=DEFAULT_VINTAGE)
    parser.add_argument(
        "--component-output",
        type=Path,
        default=ROOT / "model" / "accounting" / "f4_partial_2025.json",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=ROOT / "model" / "accounting" / "f4_partial_materialization_manifest.json",
    )
    args = parser.parse_args()

    source, zf, phase_a, phase_b, provenance = load_vintage(args.vintage)
    try:
        component, manifest = build(phase_a, phase_b, source, provenance)
    finally:
        zf.close()

    args.component_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.component_output.write_text(
        json.dumps(component, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "counts": manifest["counts"],
        "conditional_stock_cells_promoted": False,
        "status": manifest["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
