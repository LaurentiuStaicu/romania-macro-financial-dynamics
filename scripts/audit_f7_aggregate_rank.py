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
    index = {variable: i for i, variable in enumerate(vars_)}
    matrix: list[list[Fraction]] = []
    for equation in equations:
        row = [Fraction(0) for _ in vars_]
        for variable, coefficient in equation.items():
            row[index[variable]] = Fraction(coefficient)
        matrix.append(row)

    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(len(vars_)):
        candidate = next(
            (
                row
                for row in range(pivot_row, len(matrix))
                if matrix[row][column] != 0
            ),
            None,
        )
        if candidate is None:
            continue
        matrix[pivot_row], matrix[candidate] = (
            matrix[candidate],
            matrix[pivot_row],
        )
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [
            value / pivot for value in matrix[pivot_row]
        ]
        for row in range(len(matrix)):
            if row == pivot_row:
                continue
            factor = matrix[row][column]
            if factor != 0:
                matrix[row] = [
                    matrix[row][i] - factor * matrix[pivot_row][i]
                    for i in range(len(vars_))
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break

    free_columns = [
        column
        for column in range(len(vars_))
        if column not in pivot_columns
    ]
    nullspace: list[list[Fraction]] = []
    for free in free_columns:
        vector = [Fraction(0) for _ in vars_]
        vector[free] = Fraction(1)
        for row, pivot_column in enumerate(pivot_columns):
            vector[pivot_column] = -matrix[row][free]
        nullspace.append(vector)
    return len(pivot_columns), nullspace


def identify(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> dict[str, object]:
    rank, nullspace = rref_nullspace(equations, vars_)
    unique = []
    for index, variable in enumerate(vars_):
        if all(vector[index] == 0 for vector in nullspace):
            unique.append(f"{variable[0]}→{variable[1]}")
    return {
        "variables": len(vars_),
        "equations": len(equations),
        "rank": rank,
        "nullity": len(vars_) - rank,
        "unique_cell_count": len(unique),
        "unique_cells": unique,
    }


def analyze(
    measure: str,
    resident: dict[str, float | None],
    totals: dict[str, float],
) -> dict[str, object]:
    vars_ = variables()
    equations: list[dict[tuple[str, str], int]] = []
    labels: list[str] = []

    def add(equation: dict[tuple[str, str], int], label: str) -> None:
        equations.append(equation)
        labels.append(label)

    for sector in RESIDENT:
        if resident[f"{sector}_assets"] is not None:
            add(
                {(sector, issuer): 1 for issuer in SECTORS},
                f"W0-holder:{sector}",
            )
        if resident[f"{sector}_liabilities"] is not None:
            add(
                {(holder, sector): 1 for holder in SECTORS},
                f"W0-issuer:{sector}",
            )

    add(
        {(holder, issuer): 1 for holder in RESIDENT for issuer in SECTORS},
        "W0-total-assets",
    )
    add(
        {(holder, issuer): 1 for holder in SECTORS for issuer in RESIDENT},
        "W0-total-liabilities",
    )
    add(
        {(holder, "X"): 1 for holder in RESIDENT},
        "W1-assets",
    )
    add(
        {("X", issuer): 1 for issuer in RESIDENT},
        "W1-liabilities",
    )

    identification = identify(equations, vars_)

    domestic_assets = totals["W0_assets"] - totals["W1_assets"]
    domestic_liabilities = totals["W0_liabilities"] - totals["W1_liabilities"]
    residual = domestic_assets - domestic_liabilities

    complements = []
    for suffix, total_key in (
        ("assets", "W0_assets"),
        ("liabilities", "W0_liabilities"),
    ):
        missing = [
            sector
            for sector in RESIDENT
            if resident[f"{sector}_{suffix}"] is None
        ]
        if len(missing) == 1:
            known_sum = sum(
                float(resident[f"{sector}_{suffix}"])
                for sector in RESIDENT
                if resident[f"{sector}_{suffix}"] is not None
            )
            complements.append(
                {
                    "side": suffix,
                    "sector": missing[0],
                    "derived_aggregate_complement_million_RON":
                        totals[total_key] - known_sum,
                    "status": "EXACT_AGGREGATE_COMPLEMENT_ONLY",
                }
            )

    return {
        "measure": measure,
        "equation_labels": labels,
        "unconditional_identification": identification,
        "RHS_accounting_identity": {
            "domestic_from_assets_million_RON": domestic_assets,
            "domestic_from_liabilities_million_RON": domestic_liabilities,
            "residual_million_RON": residual,
            "status": "PASS" if abs(residual) <= TOL else "FAIL",
        },
        "aggregate_complements": complements,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-a-assessment",
        type=Path,
        default=Path(
            "model/accounting/f7_financial_derivatives_coverage_assessment.json"
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("f7_rank_artifacts"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    assessment = json.loads(
        args.phase_a_assessment.read_text(encoding="utf-8")
    )
    if assessment["result"]["network_errors_present"]:
        raise RuntimeError(
            "Phase A network errors block a positive rank/freeze claim"
        )

    resident = assessment["resident_aggregate_controls_million_RON"]
    totals = assessment["published_total_economy_controls_million_RON"]
    analyses = {
        "stock": analyze("stock", resident["stock"], totals["stock"]),
        "flow_2025": analyze(
            "flow_2025",
            resident["flow_2025"],
            totals["flow_2025"],
        ),
    }

    zero_unique = all(
        item["unconditional_identification"]["unique_cell_count"] == 0
        for item in analyses.values()
    )
    rhs_pass = all(
        item["RHS_accounting_identity"]["status"] == "PASS"
        for item in analyses.values()
    )

    report = {
        "audit_version": "0.1",
        "instrument": "F7",
        "phase": "exact aggregate-control rank audit",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "analyses": analyses,
        "disposition": (
            "FREEZE_F7_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY"
            if zero_unique and rhs_pass
            else "REVIEW_REQUIRED"
        ),
        "rule": (
            "Aggregate F7 controls constrain the matrix but never become "
            "bilateral allocations. Zero aggregate equations remain aggregate "
            "equations only; no non-negativity, issuer-applicability or "
            "materiality premise is introduced."
        ),
    }
    (args.out / "f7_aggregate_rank_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
