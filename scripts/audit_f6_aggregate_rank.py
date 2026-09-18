from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
TOL = 0.1


def variables() -> list[tuple[str, str]]:
    return [
        (holder, issuer)
        for holder in SECTORS
        for issuer in SECTORS
        if not (holder == "X" and issuer == "X")
    ]


def rref_nullspace(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> tuple[int, list[list[Fraction]]]:
    index = {var: i for i, var in enumerate(vars_)}
    matrix: list[list[Fraction]] = []
    for equation in equations:
        row = [Fraction(0) for _ in vars_]
        for variable, coefficient in equation.items():
            row[index[variable]] = Fraction(coefficient)
        matrix.append(row)

    rows = len(matrix)
    cols = len(vars_)
    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(cols):
        candidate = next(
            (row for row in range(pivot_row, rows) if matrix[row][column] != 0),
            None,
        )
        if candidate is None:
            continue
        matrix[pivot_row], matrix[candidate] = matrix[candidate], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]
        for row in range(rows):
            if row == pivot_row:
                continue
            factor = matrix[row][column]
            if factor != 0:
                matrix[row] = [
                    matrix[row][i] - factor * matrix[pivot_row][i]
                    for i in range(cols)
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == rows:
            break

    free_columns = [column for column in range(cols) if column not in pivot_columns]
    nullspace: list[list[Fraction]] = []
    for free_column in free_columns:
        vector = [Fraction(0) for _ in range(cols)]
        vector[free_column] = Fraction(1)
        for row, pivot_column in enumerate(pivot_columns):
            vector[pivot_column] = -matrix[row][free_column]
        nullspace.append(vector)

    return len(pivot_columns), nullspace


def identify(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> dict[str, object]:
    rank, nullspace = rref_nullspace(equations, vars_)
    unique: list[str] = []
    nonunique: list[str] = []
    for index, variable in enumerate(vars_):
        label = f"{variable[0]}→{variable[1]}"
        if all(vector[index] == 0 for vector in nullspace):
            unique.append(label)
        else:
            nonunique.append(label)
    return {
        "variables": len(vars_),
        "equations": len(equations),
        "rank": rank,
        "nullity": len(vars_) - rank,
        "unique_cell_count": len(unique),
        "nonunique_cell_count": len(nonunique),
        "unique_cells": unique,
        "nonunique_cells": nonunique,
    }


def _aggregate_value(structure: dict[str, object], sector: str, side: str) -> float:
    key = f"{sector}_{side}"
    value = structure[key]["F6"]
    return float(value)


def analyze_measure(
    structure: dict[str, object],
    total_controls: dict[str, object],
) -> dict[str, object]:
    vars_ = variables()
    equations: list[dict[tuple[str, str], int]] = []
    labels: list[str] = []

    def add(equation: dict[tuple[str, str], int], label: str) -> None:
        equations.append(equation)
        labels.append(label)

    for sector in RESIDENT:
        _aggregate_value(structure, sector, "assets")
        _aggregate_value(structure, sector, "liabilities")
        add({(sector, issuer): 1 for issuer in SECTORS}, f"W0-holder:{sector}")
        add({(holder, sector): 1 for holder in SECTORS}, f"W0-issuer:{sector}")

    w1_assets = float(total_controls["W1_assets"]["F6"])
    w1_liabilities = float(total_controls["W1_liabilities"]["F6"])
    add({(holder, "X"): 1 for holder in RESIDENT}, "W1-assets")
    add({("X", issuer): 1 for issuer in RESIDENT}, "W1-liabilities")

    identification = identify(equations, vars_)

    holder_sum = sum(
        _aggregate_value(structure, sector, "assets") for sector in RESIDENT
    )
    issuer_sum = sum(
        _aggregate_value(structure, sector, "liabilities") for sector in RESIDENT
    )
    domestic_from_assets = holder_sum - w1_assets
    domestic_from_liabilities = issuer_sum - w1_liabilities
    residual = domestic_from_assets - domestic_from_liabilities

    return {
        "equation_labels": labels,
        "unconditional_identification": identification,
        "RHS_accounting_identity": {
            "resident_holder_W0_sum_million_RON": holder_sum,
            "W1_assets_million_RON": w1_assets,
            "domestic_from_assets_million_RON": domestic_from_assets,
            "resident_issuer_W0_sum_million_RON": issuer_sum,
            "W1_liabilities_million_RON": w1_liabilities,
            "domestic_from_liabilities_million_RON": domestic_from_liabilities,
            "residual_million_RON": residual,
            "status": "PASS" if abs(residual) <= TOL else "FAIL",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-a-assessment",
        type=Path,
        default=Path("model/accounting/f6_insurance_pensions_coverage_assessment.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("f6_rank_artifacts"),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    phase_a = json.loads(args.phase_a_assessment.read_text(encoding="utf-8"))
    structure = phase_a["resident_aggregate_structure"]
    controls = phase_a["published_total_economy_controls_million_RON"]

    analyses = {
        "stock": analyze_measure(structure["stock"], controls["stock"]),
        "flow_2025": analyze_measure(structure["flow_2025"], controls["flow_2025"]),
    }

    stock = analyses["stock"]
    flow = analyses["flow_2025"]
    all_rhs_pass = (
        stock["RHS_accounting_identity"]["status"] == "PASS"
        and flow["RHS_accounting_identity"]["status"] == "PASS"
    )
    zero_unique = (
        stock["unconditional_identification"]["unique_cell_count"] == 0
        and flow["unconditional_identification"]["unique_cell_count"] == 0
    )

    report = {
        "audit_version": "0.1",
        "instrument": "F6",
        "phase": "exact aggregate-control rank audit",
        "source_assessment": str(args.phase_a_assessment),
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "analyses": analyses,
        "disposition": (
            "FREEZE_F6_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY"
            if all_rhs_pass and zero_unique
            else "REVIEW_REQUIRED"
        ),
        "reproduction_boundary": (
            "Exact rank/nullspace and RHS accounting are reproduced offline from the "
            "retained Phase A assessment. Original live source retrieval is outside "
            "this offline gate and remains subject to its separate provenance record."
        ),
        "rule": (
            "Aggregate controls constrain the F6 matrix but do not become bilateral "
            "observations. No issuer-applicability, non-negativity or missing-to-zero "
            "constraint is introduced. A bilateral coordinate is unique only if it "
            "has zero loading on every exact nullspace basis vector."
        ),
    }

    output = args.out / "f6_aggregate_rank_audit.json"
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
