from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ID = "accounting-f3-2025-vintage-2026-09-18"
SNAPSHOT = ROOT / "data" / "source_vintages" / SNAPSHOT_ID
DEFAULT_BENCHMARK = ROOT / "model" / "accounting" / "benchmark_2025.json"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
TOL = 0.1


def direct_or_derived(cell: dict[str, object]) -> tuple[str, str | None, str]:
    holder = str(cell["holder"])
    issuer = str(cell["issuer"])
    terms = cell["canonical_terms"]

    if holder == "X" and issuer == "X":
        return (
            "NOT_APPLICABLE",
            None,
            "Outside the Romanian national financial-accounts boundary: "
            "RMD represents resident-sector positions vis-a-vis the rest of the world, "
            "not positions among non-residents themselves.",
        )

    if cell["canonical_value_million_RON"] is None:
        raise RuntimeError(f"Cannot materialize unresolved F3 cell {holder}->{issuer}")

    if holder != "F" and issuer != "F":
        if len(terms) != 1 or float(terms[0]["coefficient"]) != 1.0:
            raise RuntimeError(
                f"Direct F3 cell {holder}->{issuer} does not have one exact source"
            )
        key = str(terms[0]["key"])
        return (
            "OBSERVED",
            key,
            f"Direct ECB QSA canonical observation from immutable snapshot {SNAPSHOT_ID}.",
        )

    expression = " + ".join(
        f"{float(term['coefficient']):+g}*{term['key']}"
        for term in terms
    )
    return (
        "DERIVED",
        None,
        "Exact additive sector derivation required by RMD F = S12 - S121; "
        f"snapshot={SNAPSHOT_ID}; formula={expression}",
    )


def validate_audit(audit: dict[str, object]) -> None:
    if audit["aggregate_reconciliation_status_counts"] != {"PASS": 20}:
        raise RuntimeError("F3 aggregate reconciliation gate failed")
    if audit["maturity_reconciliation_status_counts"] != {"PASS": 2}:
        raise RuntimeError("F3 maturity reconciliation gate failed")
    if audit["cell_status_counts"].get("UNRESOLVED_SOURCE_COVERAGE", 0) != 0:
        raise RuntimeError("F3 canonical source coverage is incomplete")

    stock_external = sum(
        float(cell["canonical_value_million_RON"])
        for cell in audit["cells"]
        if cell["measure"] == "stock"
        and cell["holder"] == "X"
        and cell["issuer"] != "X"
    )
    if abs(stock_external - 493246.93) > TOL:
        raise RuntimeError(
            f"External-holder F3 control mismatch: {stock_external} != 493246.93"
        )


def build_materialization(audit: dict[str, object]) -> dict[str, object]:
    cell_records = []
    counts = {
        "stock": {"OBSERVED": 0, "DERIVED": 0, "NOT_APPLICABLE": 0},
        "flow": {"OBSERVED": 0, "DERIVED": 0, "NOT_APPLICABLE": 0},
    }

    for cell in audit["cells"]:
        status, source_key, note = direct_or_derived(cell)
        measure = str(cell["measure"])
        value = (
            None
            if status == "NOT_APPLICABLE"
            else float(cell["canonical_value_million_RON"])
        )
        counts[measure][status] += 1
        cell_records.append(
            {
                "holder": cell["holder"],
                "issuer": cell["issuer"],
                "instrument": "F3",
                "measure": measure,
                "status": status,
                "value": value,
                "unit": "million_RON",
                "source_series_key": source_key,
                "canonical_terms": cell["canonical_terms"],
                "note": note,
            }
        )

    expected = {"OBSERVED": 24, "DERIVED": 11, "NOT_APPLICABLE": 1}
    for measure in ("stock", "flow"):
        if counts[measure] != expected:
            raise RuntimeError(
                f"Unexpected F3 materialization counts for {measure}: "
                f"{counts[measure]} != {expected}"
            )

    return {
        "materialization_version": "0.1",
        "instrument": "F3",
        "source_vintage": SNAPSHOT_ID,
        "benchmark_stock_period": "2025-Q4",
        "benchmark_flow_period": "2025-Q1..2025-Q4",
        "value_rule": "official published precision from the retained ECB QSA audit",
        "sector_identity": "F = S12 - S121",
        "counts": counts,
        "aggregate_reconciliation": audit["aggregate_controls"],
        "maturity_reconciliation": audit["maturity_controls"],
        "cells": cell_records,
    }


def build_benchmark(
    baseline: dict[str, object],
    materialization: dict[str, object],
) -> dict[str, object]:
    benchmark = deepcopy(baseline)

    by_measure = {
        "stock": [],
        "flow": [],
    }
    for cell in materialization["cells"]:
        override = {
            "holder": cell["holder"],
            "issuer": cell["issuer"],
            "status": cell["status"],
            "value": cell["value"],
            "unit": "million_RON",
            "note": cell["note"],
        }
        if cell["source_series_key"] is not None:
            override["source_series_key"] = cell["source_series_key"]
        by_measure[str(cell["measure"])].append(override)

    for measure in ("stock", "flow"):
        overrides = by_measure[measure]
        overrides.sort(
            key=lambda item: (
                SECTORS.index(str(item["holder"])),
                SECTORS.index(str(item["issuer"])),
            )
        )
        if len(overrides) != 36:
            raise RuntimeError(f"Expected 36 F3 {measure} overrides")
        benchmark["matrices"]["F3"][measure] = {
            "default": {
                "status": "TBD",
                "value": None,
                "unit": "million_RON",
            },
            "overrides": overrides,
        }

    benchmark["observed_anchors"] = [
        anchor
        for anchor in benchmark["observed_anchors"]
        if anchor["id"] != "qsa_nonresident_debt_securities_total_economy_2025q4"
    ]
    benchmark["observed_anchors"].append(
        {
            "id": "qsa_nonresident_debt_securities_total_economy_2025q4",
            "value": 493246.93,
            "unit": "million_RON",
            "period": "2025-Q4",
            "series_key": "QSA.Q.N.RO.W1.S1.S1.N.L.LE.F3.T._Z.XDC._T.S.V.N._T",
            "role": "independent external-holder aggregate control; exactly reproduced by the populated canonical F3 X row",
        }
    )

    return benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark-input",
        type=Path,
        default=DEFAULT_BENCHMARK,
    )
    parser.add_argument(
        "--benchmark-output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--materialization-output",
        type=Path,
        required=True,
    )
    args = parser.parse_args()

    audit = json.loads(
        (SNAPSHOT / "qsa_f3_coverage_audit.json").read_text(encoding="utf-8")
    )
    validate_audit(audit)

    baseline = json.loads(args.benchmark_input.read_text(encoding="utf-8"))
    materialization = build_materialization(audit)
    benchmark = build_benchmark(baseline, materialization)

    args.benchmark_output.parent.mkdir(parents=True, exist_ok=True)
    args.materialization_output.parent.mkdir(parents=True, exist_ok=True)
    args.benchmark_output.write_text(
        json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    args.materialization_output.write_text(
        json.dumps(materialization, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    numeric = [
        cell
        for cell in materialization["cells"]
        if cell["status"] in {"OBSERVED", "DERIVED"}
    ]
    if len(numeric) != 70:
        raise RuntimeError(f"Expected 70 numeric F3 stock/flow cells, found {len(numeric)}")
    if not all(math.isfinite(float(cell["value"])) for cell in numeric):
        raise RuntimeError("Non-finite F3 materialized value")

    print(json.dumps(materialization["counts"], indent=2))


if __name__ == "__main__":
    main()
