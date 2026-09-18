from __future__ import annotations

import json
import math
from pathlib import Path

from scripts.audit_qsa_accounting_coverage import (
    DIRECT_SECTOR,
    COMPOSITE_SECTOR,
    OUT,
    Term,
    fetch_series,
    formula_value,
    qsa_key,
)

RESIDENT_SECTORS = ("H", "C", "F", "G", "BNR")
ABS_TOLERANCE_MILLION_RON = 0.05


def sector_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in DIRECT_SECTOR:
        return ((DIRECT_SECTOR[sector], 1.0),)
    return COMPOSITE_SECTOR[sector]


def aggregate_terms(sector: str, *, entry: str, measure: str) -> tuple[Term, ...]:
    terms = []
    for sector_code, coefficient in sector_terms(sector):
        terms.append(
            Term(
                coefficient,
                qsa_key(
                    counterpart_area="W0",
                    reference_sector=sector_code,
                    counterpart_sector="S1",
                    entry=entry,
                    measure=measure,
                ),
                "aggregate_control",
            )
        )
    return tuple(terms)


def external_total_term(*, measure: str) -> tuple[Term, ...]:
    return (
        Term(
            1.0,
            qsa_key(
                counterpart_area="W1",
                reference_sector="S1",
                counterpart_sector="S1",
                entry="L",
                measure=measure,
            ),
            "external_total_control",
        ),
    )


def main() -> None:
    audit_path = OUT / "qsa_f3_coverage_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    cells = audit["cells"]

    required_keys = set()
    control_plans = []

    for measure in ("LE", "F"):
        measure_label = "stock" if measure == "LE" else "flow"

        for sector in RESIDENT_SECTORS:
            holder_terms = aggregate_terms(sector, entry="A", measure=measure)
            issuer_terms = aggregate_terms(sector, entry="L", measure=measure)
            required_keys.update(term.key for term in holder_terms)
            required_keys.update(term.key for term in issuer_terms)
            control_plans.append(
                {
                    "kind": "holder_total",
                    "sector": sector,
                    "measure": measure,
                    "measure_label": measure_label,
                    "terms": holder_terms,
                }
            )
            control_plans.append(
                {
                    "kind": "issuer_total",
                    "sector": sector,
                    "measure": measure,
                    "measure_label": measure_label,
                    "terms": issuer_terms,
                }
            )

        ext_terms = external_total_term(measure=measure)
        required_keys.update(term.key for term in ext_terms)
        control_plans.append(
            {
                "kind": "external_holder_total",
                "sector": "X",
                "measure": measure,
                "measure_label": measure_label,
                "terms": ext_terms,
            }
        )

    series_by_key = {}
    for index, key in enumerate(sorted(required_keys), start=1):
        print(f"[control {index}/{len(required_keys)}] {key}", flush=True)
        series_by_key[key] = fetch_series(key)

    results = []
    failures = 0

    for plan in control_plans:
        measure_label = plan["measure_label"]
        sector = plan["sector"]
        kind = plan["kind"]

        if kind == "holder_total":
            bilateral = sum(
                float(cell["canonical_value_million_RON"])
                for cell in cells
                if cell["measure"] == measure_label
                and cell["holder"] == sector
                and cell["canonical_value_million_RON"] is not None
            )
        elif kind == "issuer_total":
            bilateral = sum(
                float(cell["canonical_value_million_RON"])
                for cell in cells
                if cell["measure"] == measure_label
                and cell["issuer"] == sector
                and cell["canonical_value_million_RON"] is not None
            )
        elif kind == "external_holder_total":
            bilateral = sum(
                float(cell["canonical_value_million_RON"])
                for cell in cells
                if cell["measure"] == measure_label
                and cell["holder"] == "X"
                and cell["issuer"] != "X"
                and cell["canonical_value_million_RON"] is not None
            )
        else:
            raise ValueError(kind)

        official, detail = formula_value(
            plan["terms"],
            series_by_key,
            measure=plan["measure"],
        )

        if official is None:
            status = "CONTROL_UNAVAILABLE"
            residual = None
            failures += 1
        else:
            residual = bilateral - float(official)
            status = (
                "PASS"
                if math.isfinite(residual)
                and abs(residual) <= ABS_TOLERANCE_MILLION_RON
                else "FAIL"
            )
            if status != "PASS":
                failures += 1

        results.append(
            {
                "kind": kind,
                "sector": sector,
                "measure": measure_label,
                "bilateral_sum_million_RON": bilateral,
                "official_aggregate_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
                "official_detail": detail,
            }
        )

    report = {
        "audit_version": "0.1",
        "purpose": "Independent aggregate reconciliation of candidate F3 bilateral cells against official ECB QSA W0/W1 totals.",
        "absolute_tolerance_million_RON": ABS_TOLERANCE_MILLION_RON,
        "control_count": len(results),
        "failure_count": failures,
        "all_controls_pass": failures == 0,
        "controls": results,
    }

    (OUT / "qsa_f3_aggregate_controls.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "control_count": len(results),
                "failure_count": failures,
                "all_controls_pass": failures == 0,
                "controls": [
                    {
                        "kind": item["kind"],
                        "sector": item["sector"],
                        "measure": item["measure"],
                        "residual_million_RON": item["residual_million_RON"],
                        "status": item["status"],
                    }
                    for item in results
                ],
            },
            indent=2,
        )
    )

    if failures:
        raise SystemExit(
            f"F3 aggregate-control audit failed: {failures} controls unavailable or outside tolerance"
        )


if __name__ == "__main__":
    main()
