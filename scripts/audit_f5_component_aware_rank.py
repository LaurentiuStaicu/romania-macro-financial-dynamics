from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

COMPONENTS = ("F511", "F512", "F519", "F52")
EQUITY_COMPONENTS = ("F511", "F512", "F519")
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")


def variables() -> list[tuple[str, str, str]]:
    return [
        (component, holder, issuer)
        for component in COMPONENTS
        for holder in SECTORS
        for issuer in SECTORS
        if not (holder == "X" and issuer == "X")
    ]


def rref_nullspace(
    equations: list[dict[tuple[str, str, str], int]],
    vars_: list[tuple[str, str, str]],
) -> tuple[int, list[list[Fraction]]]:
    index = {v: i for i, v in enumerate(vars_)}
    matrix = []
    for eq in equations:
        row = [Fraction(0) for _ in vars_]
        for var, coeff in eq.items():
            row[index[var]] = Fraction(coeff)
        matrix.append(row)

    rows = len(matrix)
    cols = len(vars_)
    pivot_cols: list[int] = []
    pivot_row = 0
    for col in range(cols):
        candidate = next(
            (r for r in range(pivot_row, rows) if matrix[r][col] != 0),
            None,
        )
        if candidate is None:
            continue
        matrix[pivot_row], matrix[candidate] = matrix[candidate], matrix[pivot_row]
        pivot = matrix[pivot_row][col]
        matrix[pivot_row] = [x / pivot for x in matrix[pivot_row]]
        for r in range(rows):
            if r == pivot_row:
                continue
            factor = matrix[r][col]
            if factor != 0:
                matrix[r] = [
                    matrix[r][c] - factor * matrix[pivot_row][c]
                    for c in range(cols)
                ]
        pivot_cols.append(col)
        pivot_row += 1
        if pivot_row == rows:
            break

    free_cols = [c for c in range(cols) if c not in pivot_cols]
    nullspace = []
    for free in free_cols:
        vector = [Fraction(0) for _ in range(cols)]
        vector[free] = Fraction(1)
        for r, pivot_col in enumerate(pivot_cols):
            vector[pivot_col] = -matrix[r][free]
        nullspace.append(vector)
    return len(pivot_cols), nullspace


def subset(
    component: str,
    area: str,
    entry: str,
) -> list[tuple[str, str, str]]:
    if area == "W0" and entry == "A":
        return [(component, h, i) for h in RESIDENT for i in SECTORS]
    if area == "W0" and entry == "L":
        return [(component, h, i) for i in RESIDENT for h in SECTORS]
    if area == "W1" and entry == "A":
        return [(component, h, "X") for h in RESIDENT]
    if area == "W1" and entry == "L":
        return [(component, "X", i) for i in RESIDENT]
    raise ValueError((area, entry))


def build_equations(report: dict, measure: str):
    vars_ = variables()
    equations: list[dict[tuple[str, str, str], int]] = []
    labels: list[str] = []

    def add(coeffs: dict[tuple[str, str, str], int], label: str) -> None:
        equations.append(coeffs)
        labels.append(label)

    for cell in report["cells"]:
        if cell["measure"] != measure:
            continue
        if cell["status"] == "OUTSIDE_BOUNDARY_NOT_APPLICABLE":
            continue
        h, i = cell["holder"], cell["issuer"]
        for component in EQUITY_COMPONENTS:
            item = cell["F51"]["components"][component]
            if item["status"] == "OBSERVABLE_OR_EXACT_DERIVATION":
                add({(component, h, i): 1}, f"direct:{component}:{h}→{i}")
        f52 = cell["F52"]
        if f52["status"] in {
            "OBSERVABLE_OR_EXACT_DERIVATION",
            "STRUCTURAL_NOT_APPLICABLE_RESIDENT_NONFUND_ISSUER",
        }:
            add({("F52", h, i): 1}, f"{f52['status']}:F52:{h}→{i}")

    f5_aggregate = {
        (x["measure"], x["kind"], x["sector"]):
            x["official_F5_aggregate_million_RON"]
        for x in report["aggregate_F5_reconciliation"]
    }

    for item in report["sector_F51_equals_components_controls"]:
        if item["measure"] != measure:
            continue
        sector = item["sector"]
        entry = item["entry"]
        kind = "holder_total" if entry == "A" else "issuer_total"

        if f5_aggregate[(measure, kind, sector)] is not None:
            coeffs = {}
            for component in COMPONENTS:
                if entry == "A":
                    for issuer in SECTORS:
                        coeffs[(component, sector, issuer)] = 1
                else:
                    for holder in SECTORS:
                        coeffs[(component, holder, sector)] = 1
            add(coeffs, f"W0:F5:{kind}:{sector}")

        if item["F51_million_RON"] is not None:
            coeffs = {}
            for component in EQUITY_COMPONENTS:
                if entry == "A":
                    for issuer in SECTORS:
                        coeffs[(component, sector, issuer)] = 1
                else:
                    for holder in SECTORS:
                        coeffs[(component, holder, sector)] = 1
            add(coeffs, f"W0:F51:{kind}:{sector}")

        for component in EQUITY_COMPONENTS:
            if item[f"{component}_million_RON"] is None:
                continue
            if entry == "A":
                coeffs = {
                    (component, sector, issuer): 1 for issuer in SECTORS
                }
            else:
                coeffs = {
                    (component, holder, sector): 1 for holder in SECTORS
                }
            add(coeffs, f"W0:{component}:{kind}:{sector}")

    for item in report["total_F51_equals_components_controls"]:
        if item["measure"] != measure:
            continue
        area = item["area"]
        entry = item["entry"]

        if item["F5_million_RON"] is not None:
            add(
                {
                    var: 1
                    for component in COMPONENTS
                    for var in subset(component, area, entry)
                },
                f"{area}:F5:{entry}",
            )

        if item["F51_million_RON"] is not None:
            add(
                {
                    var: 1
                    for component in EQUITY_COMPONENTS
                    for var in subset(component, area, entry)
                },
                f"{area}:F51:{entry}",
            )

        for component in EQUITY_COMPONENTS:
            if item[f"{component}_million_RON"] is not None:
                add(
                    {var: 1 for var in subset(component, area, entry)},
                    f"{area}:{component}:{entry}",
                )

    return vars_, equations, labels


def analyze(report: dict, measure: str) -> dict:
    vars_, equations, labels = build_equations(report, measure)
    rank, nullspace = rref_nullspace(equations, vars_)
    index = {v: i for i, v in enumerate(vars_)}

    unique_components = []
    for i, var in enumerate(vars_):
        if all(vector[i] == 0 for vector in nullspace):
            unique_components.append(f"{var[0]}:{var[1]}→{var[2]}")

    unique_f51 = []
    unique_f5 = []
    for holder in SECTORS:
        for issuer in SECTORS:
            if holder == "X" and issuer == "X":
                continue
            f51_indices = [
                index[(component, holder, issuer)]
                for component in EQUITY_COMPONENTS
            ]
            f5_indices = [
                index[(component, holder, issuer)]
                for component in COMPONENTS
            ]
            if all(
                sum(vector[i] for i in f51_indices) == 0
                for vector in nullspace
            ):
                unique_f51.append(f"{holder}→{issuer}")
            if all(
                sum(vector[i] for i in f5_indices) == 0
                for vector in nullspace
            ):
                unique_f5.append(f"{holder}→{issuer}")

    unique_f52 = []
    for holder in SECTORS:
        for issuer in SECTORS:
            if holder == "X" and issuer == "X":
                continue
            i = index[("F52", holder, issuer)]
            if all(vector[i] == 0 for vector in nullspace):
                unique_f52.append(f"{holder}→{issuer}")

    return {
        "variables": len(vars_),
        "equations": len(equations),
        "rank": rank,
        "nullity": len(vars_) - rank,
        "unique_component_variable_count": len(unique_components),
        "unique_component_variables": unique_components,
        "unique_F52_cell_count": len(unique_f52),
        "unique_F52_cells": unique_f52,
        "unique_F51_total_cell_count": len(unique_f51),
        "unique_F51_total_cells": unique_f51,
        "unique_F5_total_cell_count": len(unique_f5),
        "unique_F5_total_cells": unique_f5,
        "equation_labels": labels,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-c-report",
        type=Path,
        default=Path("f5_phase_c_artifacts/f5_equity_subcomponent_bridge_audit.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("f5_rank_artifacts"),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    report = json.loads(args.phase_c_report.read_text(encoding="utf-8"))
    if report["instrument"] != "F5":
        raise RuntimeError("Phase C report is not F5")
    if report["network_errors_present"]:
        raise RuntimeError("Phase C network errors block rank-source claims")

    stock = analyze(report, "stock")
    flow = analyze(report, "flow")

    result = {
        "audit_version": "0.1",
        "instrument": "F5",
        "phase": "component-aware exact rank/nullspace audit",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "phase_C_source_summary": {
            "series_requested": report["series_requested"],
            "series_status_counts": report["series_status_counts"],
            "equity_component_cell_status_counts":
                report["equity_component_cell_status_counts"],
            "F52_cell_status_counts": report["F52_cell_status_counts"],
            "network_errors_present": report["network_errors_present"],
        },
        "stock": stock,
        "flow": flow,
        "disposition": (
            "FREEZE_F5_PUBLIC_DATA_BOUNDARY"
            if stock["unique_F5_total_cell_count"] == 0
            and flow["unique_F5_total_cell_count"] == 0
            else "PARTIAL_F5_TOTAL_IDENTIFICATION_REQUIRES_NEXT_GATE"
        ),
        "rule": (
            "Rank is computed on component variables. A total F5 cell is unique "
            "only when its F511+F512+F519+F52 linear form is invariant over every "
            "exact nullspace basis vector. No RHS rounding residual is forced to zero."
        ),
    }
    (args.out / "f5_component_aware_rank_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "stock": {
            "variables": stock["variables"],
            "equations": stock["equations"],
            "rank": stock["rank"],
            "nullity": stock["nullity"],
            "unique_component_variable_count": stock["unique_component_variable_count"],
            "unique_F51_total_cell_count": stock["unique_F51_total_cell_count"],
            "unique_F5_total_cell_count": stock["unique_F5_total_cell_count"],
        },
        "flow": {
            "variables": flow["variables"],
            "equations": flow["equations"],
            "rank": flow["rank"],
            "nullity": flow["nullity"],
            "unique_component_variable_count": flow["unique_component_variable_count"],
            "unique_F51_total_cell_count": flow["unique_F51_total_cell_count"],
            "unique_F5_total_cell_count": flow["unique_F5_total_cell_count"],
        },
        "disposition": result["disposition"],
    }, indent=2))


if __name__ == "__main__":
    main()
