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


def identify(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> dict[str, object]:
    rank, nullspace = rref_nullspace(equations, vars_)
    unique = []
    nonunique = []
    for i, var in enumerate(vars_):
        label = f"{var[0]}→{var[1]}"
        if all(vec[i] == 0 for vec in nullspace):
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-a-report",
        type=Path,
        default=Path("f8_phase_a_artifacts/f8_other_accounts_coverage_audit.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("f8_rank_artifacts"),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    phase_a = json.loads(args.phase_a_report.read_text(encoding="utf-8"))
    if phase_a["instrument"] != "F8":
        raise RuntimeError("Phase A report is not F8")
    if phase_a["network_errors_present"]:
        raise RuntimeError("Phase A network errors block a positive rank claim")
    if phase_a["cell_status_counts"].get("OBSERVABLE_OR_EXACT_DERIVATION", 0) != 0:
        raise RuntimeError("Phase C expects zero direct bilateral total-F8 cells")

    aggregate = {
        (r["measure"], r["kind"], r["sector"]): r
        for r in phase_a["aggregate_reconciliation"]
    }
    totals = {
        (r["measure"], r["area"], r["entry"], r["instrument"]): r
        for r in phase_a["total_economy_controls"]
    }

    vars_ = variables()
    analyses = {}

    for measure in ("stock", "flow"):
        equations: list[dict[tuple[str, str], int]] = []
        labels: list[str] = []

        def add(eq: dict[tuple[str, str], int], label: str) -> None:
            equations.append(eq)
            labels.append(label)

        for sector in RESIDENT:
            holder = aggregate[(measure, "holder_total", sector)]
            issuer = aggregate[(measure, "issuer_total", sector)]
            if holder["official_aggregate_million_RON"] is None:
                raise RuntimeError(f"Missing W0 holder control: {measure} {sector}")
            if issuer["official_aggregate_million_RON"] is None:
                raise RuntimeError(f"Missing W0 issuer control: {measure} {sector}")
            add({(sector, i): 1 for i in SECTORS}, f"W0-holder:{sector}")
            add({(h, sector): 1 for h in SECTORS}, f"W0-issuer:{sector}")

        w1_asset = totals[(measure, "W1", "A", "F8")]["value_million_RON"]
        w1_liability = totals[(measure, "W1", "L", "F8")]["value_million_RON"]
        if w1_asset is None or w1_liability is None:
            raise RuntimeError(f"Missing W1 F8 controls for {measure}")
        add({(h, "X"): 1 for h in RESIDENT}, "W1-assets")
        add({("X", i): 1 for i in RESIDENT}, "W1-liabilities")

        base = identify(equations, vars_)

        holder_sum = sum(
            float(aggregate[(measure, "holder_total", s)]["official_aggregate_million_RON"])
            for s in RESIDENT
        )
        issuer_sum = sum(
            float(aggregate[(measure, "issuer_total", s)]["official_aggregate_million_RON"])
            for s in RESIDENT
        )
        domestic_from_assets = holder_sum - float(w1_asset)
        domestic_from_liabilities = issuer_sum - float(w1_liability)
        identity_residual = domestic_from_assets - domestic_from_liabilities
        identity_status = "PASS" if abs(identity_residual) <= TOL else "FAIL"

        conditional = None
        bnr_zero_pass = False
        if measure == "stock":
            bnr = aggregate[(measure, "issuer_total", "BNR")]
            bnr_zero_pass = (
                bnr["official_aggregate_million_RON"] is not None
                and abs(float(bnr["official_aggregate_million_RON"])) <= TOL
            )
            if bnr_zero_pass:
                conditional_equations = list(equations)
                for holder in SECTORS:
                    conditional_equations.append({(holder, "BNR"): 1})
                conditional = identify(conditional_equations, vars_)

        analyses[measure] = {
            "equation_labels": labels,
            "unconditional_identification": base,
            "RHS_accounting_identity": {
                "resident_holder_W0_sum_million_RON": holder_sum,
                "W1_assets_million_RON": w1_asset,
                "domestic_from_assets_million_RON": domestic_from_assets,
                "resident_issuer_W0_sum_million_RON": issuer_sum,
                "W1_liabilities_million_RON": w1_liability,
                "domestic_from_liabilities_million_RON": domestic_from_liabilities,
                "residual_million_RON": identity_residual,
                "status": identity_status,
            },
            "stock_BNR_zero_condition_pass": bnr_zero_pass if measure == "stock" else None,
            "conditional_stock_BNR_zero_identification": conditional,
        }

    report = {
        "audit_version": "0.1",
        "instrument": "F8",
        "phase": "exact aggregate-control rank audit",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "phase_A_source_summary": {
            "series_requested": phase_a["series_requested"],
            "series_status_counts": phase_a["series_status_counts"],
            "cell_status_counts": phase_a["cell_status_counts"],
            "network_errors_present": phase_a["network_errors_present"],
        },
        "analyses": analyses,
        "disposition": (
            "FREEZE_F8_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY"
            if analyses["stock"]["unconditional_identification"]["unique_cell_count"] == 0
            and analyses["flow"]["unconditional_identification"]["unique_cell_count"] == 0
            else "UNCONDITIONAL_PARTIAL_CORE_EXISTS_REVIEW_BEFORE_NEXT_GATE"
        ),
        "rule": (
            "Aggregate controls constrain the F8 matrix but do not become bilateral "
            "observations. A cell is unique only if it has zero loading on every "
            "exact nullspace basis vector. Conditional BNR stock zeros are reported "
            "separately and are never promoted by this phase."
        ),
    }

    (args.out / "f8_aggregate_rank_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "stock": analyses["stock"]["unconditional_identification"],
        "flow": analyses["flow"]["unconditional_identification"],
        "stock_conditional_BNR_zero":
            analyses["stock"]["conditional_stock_BNR_zero_identification"],
        "stock_RHS_identity":
            analyses["stock"]["RHS_accounting_identity"],
        "flow_RHS_identity":
            analyses["flow"]["RHS_accounting_identity"],
        "disposition": report["disposition"],
    }, indent=2))


if __name__ == "__main__":
    main()
