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


def parse_cell(label: str) -> tuple[str, str]:
    parts = label.split("→")
    if len(parts) != 2 or parts[0] not in SECTORS or parts[1] not in SECTORS:
        raise RuntimeError(f"Invalid F5 topology cell: {label}")
    if parts == ["X", "X"]:
        raise RuntimeError("X→X is outside the F5 national-accounts boundary")
    return parts[0], parts[1]


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
    raise RuntimeError(f"Invalid aggregate topology address: {area} {entry}")


def validate_snapshot(snapshot: dict[str, object]) -> None:
    if snapshot.get("instrument") != "F5":
        raise RuntimeError("Retained rank topology snapshot is not F5")
    provenance = snapshot.get("provenance")
    if not isinstance(provenance, dict):
        raise RuntimeError("F5 snapshot provenance is missing")
    if provenance.get("network_errors_present") is not False:
        raise RuntimeError("F5 topology must originate from a no-network-error run")
    if int(provenance.get("series_requested", 0)) <= 0:
        raise RuntimeError("F5 topology source-series count is missing")
    topology = snapshot.get("coefficient_topology")
    if not isinstance(topology, dict):
        raise RuntimeError("F5 coefficient topology is missing")
    if topology.get("same_for_stock_and_flow") is not True:
        raise RuntimeError(
            "F5 retained topology must explicitly match stock and flow"
        )
    boundary = snapshot.get("hard_boundary")
    if not isinstance(boundary, dict):
        raise RuntimeError("F5 snapshot hard boundary is missing")
    for key in (
        "benchmark_mutation",
        "materialization",
        "synthetic_allocation",
        "missing_to_zero",
        "behavioural_closure_changed",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(
                f"F5 retained topology violates hard boundary: {key}"
            )


def build_equations(
    snapshot: dict[str, object],
) -> tuple[
    list[tuple[str, str, str]],
    list[dict[tuple[str, str, str], int]],
    list[str],
]:
    vars_ = variables()
    equations: list[dict[tuple[str, str, str], int]] = []
    labels: list[str] = []

    def add(coeffs: dict[tuple[str, str, str], int], label: str) -> None:
        equations.append(coeffs)
        labels.append(label)

    topology = snapshot["coefficient_topology"]

    for component in EQUITY_COMPONENTS:
        for label in topology["direct_equity_component_cells"][component]:
            holder, issuer = parse_cell(label)
            add(
                {(component, holder, issuer): 1},
                f"direct:{component}:{label}",
            )

    structural_issuers = topology["F52"]["structural_nonfund_resident_issuers"]
    if set(structural_issuers) != {"H", "C", "G", "BNR"}:
        raise RuntimeError(
            "Retained F52 structural issuer scope differs from the Phase C contract"
        )
    for issuer in structural_issuers:
        for holder in SECTORS:
            add(
                {("F52", holder, issuer): 1},
                "STRUCTURAL_NOT_APPLICABLE_RESIDENT_NONFUND_ISSUER:"
                f"F52:{holder}→{issuer}",
            )

    for label in topology["F52"]["direct_cells"]:
        holder, issuer = parse_cell(label)
        add({("F52", holder, issuer): 1}, f"direct:F52:{label}")

    resident_topology = topology["resident_aggregate_equations"]
    expected_resident = {
        f"{sector}:{entry}"
        for sector in RESIDENT
        for entry in ("A", "L")
    }
    if set(resident_topology) != expected_resident:
        raise RuntimeError("Incomplete F5 resident aggregate topology")

    for address, instruments in resident_topology.items():
        sector, entry = address.split(":")
        kind = "holder_total" if entry == "A" else "issuer_total"

        if "F5" in instruments:
            coeffs: dict[tuple[str, str, str], int] = {}
            for component in COMPONENTS:
                if entry == "A":
                    for issuer in SECTORS:
                        coeffs[(component, sector, issuer)] = 1
                else:
                    for holder in SECTORS:
                        coeffs[(component, holder, sector)] = 1
            add(coeffs, f"W0:F5:{kind}:{sector}")

        if "F51" in instruments:
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
            if component not in instruments:
                continue
            if entry == "A":
                coeffs = {
                    (component, sector, issuer): 1
                    for issuer in SECTORS
                }
            else:
                coeffs = {
                    (component, holder, sector): 1
                    for holder in SECTORS
                }
            add(coeffs, f"W0:{component}:{kind}:{sector}")

    total_topology = topology["total_aggregate_equations"]
    expected_total = {
        f"{area}:{entry}"
        for area in ("W0", "W1")
        for entry in ("A", "L")
    }
    if set(total_topology) != expected_total:
        raise RuntimeError("Incomplete F5 total aggregate topology")

    for address, instruments in total_topology.items():
        area, entry = address.split(":")

        if "F5" in instruments:
            add(
                {
                    var: 1
                    for component in COMPONENTS
                    for var in subset(component, area, entry)
                },
                f"{area}:F5:{entry}",
            )

        if "F51" in instruments:
            add(
                {
                    var: 1
                    for component in EQUITY_COMPONENTS
                    for var in subset(component, area, entry)
                },
                f"{area}:F51:{entry}",
            )

        for component in EQUITY_COMPONENTS:
            if component in instruments:
                add(
                    {
                        var: 1
                        for var in subset(component, area, entry)
                    },
                    f"{area}:{component}:{entry}",
                )

    return vars_, equations, labels


def analyze(snapshot: dict[str, object]) -> dict[str, object]:
    vars_, equations, labels = build_equations(snapshot)
    rank, nullspace = rref_nullspace(equations, vars_)
    index = {v: i for i, v in enumerate(vars_)}

    unique_components = []
    for i, var in enumerate(vars_):
        if all(vector[i] == 0 for vector in nullspace):
            unique_components.append(f"{var[0]}:{var[1]}→{var[2]}")

    unique_f52 = []
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
            f52_index = index[("F52", holder, issuer)]

            if all(
                vector[f52_index] == 0
                for vector in nullspace
            ):
                unique_f52.append(f"{holder}→{issuer}")
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
        "--topology-snapshot",
        type=Path,
        default=Path(
            "model/accounting/f5_rank_topology_snapshot_2025.json"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("f5_rank_artifacts"),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    snapshot = json.loads(
        args.topology_snapshot.read_text(encoding="utf-8")
    )
    validate_snapshot(snapshot)

    stock = analyze(snapshot)
    flow = analyze(snapshot)

    result = {
        "audit_version": "0.2",
        "instrument": "F5",
        "phase": "component-aware exact rank/nullspace audit",
        "topology_snapshot": str(args.topology_snapshot),
        "source_provenance": snapshot["provenance"],
        "reproduction_mode": "OFFLINE_RETAINED_COEFFICIENT_TOPOLOGY",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "stock": stock,
        "flow": flow,
        "disposition": (
            "FREEZE_F5_PUBLIC_DATA_BOUNDARY"
            if stock["unique_F5_total_cell_count"] == 0
            and flow["unique_F5_total_cell_count"] == 0
            else "PARTIAL_F5_TOTAL_IDENTIFICATION_REQUIRES_NEXT_GATE"
        ),
        "reproduction_boundary": (
            "Phase D is a coefficient-rank/topology claim. It is reproduced "
            "offline from the retained equation-admissibility topology extracted "
            "from the successful Phase C workflow artifact identified by SHA-256. "
            "No RHS value is needed or introduced by this rank-only gate. Fresh "
            "source coverage remains separate."
        ),
        "rule": (
            "Rank is computed on component variables. A total F5 cell is unique "
            "only when its F511+F512+F519+F52 linear form is invariant over every "
            "exact nullspace basis vector. No source absence is converted into a "
            "zero equation."
        ),
    }
    (args.out / "f5_component_aware_rank_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "stock": {
            key: stock[key]
            for key in (
                "variables",
                "equations",
                "rank",
                "nullity",
                "unique_component_variable_count",
                "unique_F52_cell_count",
                "unique_F51_total_cell_count",
                "unique_F5_total_cell_count",
            )
        },
        "flow": {
            key: flow[key]
            for key in (
                "variables",
                "equations",
                "rank",
                "nullity",
                "unique_component_variable_count",
                "unique_F52_cell_count",
                "unique_F51_total_cell_count",
                "unique_F5_total_cell_count",
            )
        },
        "reproduction_mode": result["reproduction_mode"],
        "disposition": result["disposition"],
    }, indent=2))


if __name__ == "__main__":
    main()
