from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "model" / "accounting" / "accounting_readiness_gate.json"
BENCHMARK_PATH = ROOT / "model" / "accounting" / "benchmark_2025.json"
RECONCILIATION_PATH = ROOT / "model" / "accounting" / "reconciliation_2025.json"

SECTORS = ("H", "C", "F", "G", "X", "BNR")
MEASURES = ("stock", "flow")
NUMERIC_STATUSES = {"OBSERVED", "DERIVED"}
COMPLETE_STATUSES = NUMERIC_STATUSES | {"NOT_APPLICABLE"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expanded_cells(matrix_spec: dict) -> list[dict[str, object]]:
    default = matrix_spec.get("default", {})
    overrides: dict[tuple[str, str], dict] = {}
    for raw in matrix_spec.get("overrides", []):
        address = (raw["holder"], raw["issuer"])
        if address in overrides:
            raise RuntimeError(
                f"Duplicate benchmark override for {address[0]}→{address[1]}"
            )
        overrides[address] = raw

    cells: list[dict[str, object]] = []
    for holder in SECTORS:
        for issuer in SECTORS:
            override = overrides.get((holder, issuer), {})
            status = override.get("status", default.get("status", "TBD"))
            value = (
                override["value"]
                if "value" in override
                else default.get("value")
            )
            cells.append(
                {
                    "holder": holder,
                    "issuer": issuer,
                    "status": status,
                    "value": value,
                }
            )
    return cells


def matrix_readiness(matrix_spec: dict) -> dict[str, object]:
    cells = expanded_cells(matrix_spec)
    if len(cells) != 36:
        raise RuntimeError("Canonical matrix must expand to 36 addresses")

    errors: list[str] = []
    status_counts = Counter(str(cell["status"]) for cell in cells)

    for cell in cells:
        holder = str(cell["holder"])
        issuer = str(cell["issuer"])
        status = str(cell["status"])
        value = cell["value"]
        address = f"{holder}→{issuer}"

        if status in NUMERIC_STATUSES:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{address} {status} lacks a real numeric value")
            elif not math.isfinite(float(value)):
                errors.append(f"{address} {status} is non-finite")
        elif status == "NOT_APPLICABLE":
            if value is not None:
                errors.append(f"{address} NOT_APPLICABLE carries a numeric value")

    x_to_x = next(
        cell
        for cell in cells
        if cell["holder"] == "X" and cell["issuer"] == "X"
    )
    in_boundary = [
        cell
        for cell in cells
        if not (cell["holder"] == "X" and cell["issuer"] == "X")
    ]

    complete = (
        not errors
        and str(x_to_x["status"]) == "NOT_APPLICABLE"
        and all(str(cell["status"]) in NUMERIC_STATUSES for cell in in_boundary)
    )

    unresolved = [
        f"{cell['holder']}→{cell['issuer']}:{cell['status']}"
        for cell in cells
        if str(cell["status"]) not in COMPLETE_STATUSES
    ]

    return {
        "complete": complete,
        "status_counts": dict(status_counts),
        "finite_numeric_in_boundary_cells": sum(
            1
            for cell in in_boundary
            if str(cell["status"]) in NUMERIC_STATUSES
            and isinstance(cell["value"], (int, float))
            and not isinstance(cell["value"], bool)
            and math.isfinite(float(cell["value"]))
        ),
        "unresolved_cell_count": len(unresolved),
        "unresolved_cells": unresolved,
        "integrity_errors": errors,
        "X_to_X_status": str(x_to_x["status"]),
    }


def audit_readiness(
    gate: dict,
    benchmark: dict,
    reconciliation: dict,
) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []

    canonical = list(gate["canonical_instruments"])
    if list(benchmark.get("instrument_priority", [])) != canonical:
        errors.append(
            "Benchmark instrument priority differs from Accounting Readiness Gate"
        )

    matrices = benchmark.get("matrices", {})
    if set(matrices) != set(canonical):
        errors.append("Benchmark canonical instrument set differs from readiness gate")

    instruments: dict[str, object] = {}
    for instrument in canonical:
        if instrument not in matrices:
            continue
        instrument_result = {
            measure: matrix_readiness(matrices[instrument][measure])
            for measure in MEASURES
        }
        instrument_result["stock_complete"] = instrument_result["stock"]["complete"]
        instrument_result["stock_and_flow_complete"] = (
            instrument_result["stock"]["complete"]
            and instrument_result["flow"]["complete"]
        )
        instruments[instrument] = instrument_result

    complete_stock = [
        instrument
        for instrument in canonical
        if instruments.get(instrument, {}).get("stock_complete") is True
    ]
    complete_stock_flow = [
        instrument
        for instrument in canonical
        if instruments.get(instrument, {}).get("stock_and_flow_complete") is True
    ]
    incomplete = [
        instrument
        for instrument in canonical
        if instrument not in complete_stock_flow
    ]

    expected = gate["current_expected_state"]
    if complete_stock != expected["canonical_complete_stock_instruments"]:
        errors.append(
            "Computed complete stock instruments differ from declared current state: "
            f"{complete_stock} != {expected['canonical_complete_stock_instruments']}"
        )
    if complete_stock_flow != expected["canonical_complete_stock_and_flow_instruments"]:
        errors.append(
            "Computed complete stock+flow instruments differ from declared current state: "
            f"{complete_stock_flow} != "
            f"{expected['canonical_complete_stock_and_flow_instruments']}"
        )
    if incomplete != expected["canonical_incomplete_instruments"]:
        errors.append(
            "Computed incomplete instruments differ from declared current state: "
            f"{incomplete} != {expected['canonical_incomplete_instruments']}"
        )

    stock_ready = len(complete_stock) == len(canonical)
    stock_flow_ready = len(complete_stock_flow) == len(canonical)
    if stock_ready != expected["canonical_multi_instrument_stock_initialization_ready"]:
        errors.append("Declared stock-initialization readiness disagrees with benchmark")
    if stock_flow_ready != expected["canonical_full_2025_stock_flow_benchmark_ready"]:
        errors.append("Declared full stock-flow readiness disagrees with benchmark")

    reconciliation_by_instrument = {
        item["instrument"]: item
        for item in reconciliation["instrument_gates"]
    }
    for instrument in canonical:
        item = reconciliation_by_instrument.get(instrument)
        if item is None:
            errors.append(f"Reconciliation ledger missing {instrument}")
            continue
        canonical_complete = instrument in complete_stock_flow
        labels_complete = (
            str(item["stock_matrix_status"]).startswith("COMPLETE_")
            and str(item["flow_matrix_status"]).startswith("COMPLETE_")
        )
        if canonical_complete and not labels_complete:
            errors.append(
                f"{instrument} benchmark is complete but reconciliation does not say COMPLETE"
            )
        if not canonical_complete and labels_complete:
            errors.append(
                f"{instrument} reconciliation overstates canonical completion"
            )

    for artifact in gate["noncanonical_recovery_artifacts"]:
        path = ROOT / artifact["path"]
        if not path.is_file():
            errors.append(
                f"Declared recovery artifact is missing: {artifact['path']}"
            )
        if any(
            bool(value)
            for key, value in artifact.items()
            if key.startswith("may_count_as_complete_")
        ):
            errors.append(
                f"Noncanonical recovery artifact incorrectly counts as completion: "
                f"{artifact['path']}"
            )

    in_boundary_per_matrix = int(
        gate["boundary_rule"]["in_boundary_cells_per_instrument_matrix"]
    )
    report = {
        "status": "PASS" if not errors else "FAIL",
        "canonical_instruments": canonical,
        "instrument_readiness": instruments,
        "canonical_complete_stock_instruments": complete_stock,
        "canonical_complete_stock_and_flow_instruments": complete_stock_flow,
        "canonical_incomplete_instruments": incomplete,
        "canonical_multi_instrument_stock_initialization_ready": stock_ready,
        "canonical_full_2025_stock_flow_benchmark_ready": stock_flow_ready,
        "canonical_stock_in_boundary_cells_finite": sum(
            int(instruments[instrument]["stock"]["finite_numeric_in_boundary_cells"])
            for instrument in canonical
        ),
        "canonical_stock_in_boundary_cells_required":
            len(canonical) * in_boundary_per_matrix,
        "canonical_flow_in_boundary_cells_finite": sum(
            int(instruments[instrument]["flow"]["finite_numeric_in_boundary_cells"])
            for instrument in canonical
        ),
        "canonical_flow_in_boundary_cells_required":
            len(canonical) * in_boundary_per_matrix,
        "full_RMD_empirical_state_claim_allowed": stock_flow_ready,
        "instrument_specific_complete_scope_allowed": complete_stock_flow,
    }
    return report, errors


def main() -> None:
    gate = load(GATE_PATH)
    benchmark = load(BENCHMARK_PATH)
    reconciliation = load(RECONCILIATION_PATH)
    report, errors = audit_readiness(gate, benchmark, reconciliation)
    if errors:
        raise RuntimeError(
            "Accounting Readiness Gate failed:\n- " + "\n- ".join(errors)
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
