from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_qsa_accounting_coverage import (
    CANONICAL_SECTORS,
    OUT,
    Term,
    fetch_series,
    formula_value,
    qsa_key,
    sector_terms,
)

RESIDENT_SECTORS = ("H", "C", "F", "G", "BNR")
ABS_TOLERANCE_MILLION_RON = 0.1


def world_total_terms(sector: str, *, entry: str, measure: str) -> tuple[Term, ...]:
    return tuple(
        Term(
            coefficient,
            qsa_key(
                counterpart_area="W0",
                reference_sector=code,
                counterpart_sector="S1",
                entry=entry,
                measure=measure,
            ),
            f"W0_{entry}",
        )
        for code, coefficient in sector_terms(sector)
    )


def qsa_key_maturity(
    *,
    counterpart_area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
    measure: str,
    maturity: str,
) -> str:
    return ".".join(
        (
            "Q",
            "N",
            "RO",
            counterpart_area,
            reference_sector,
            counterpart_sector,
            "N",
            entry,
            measure,
            "F3",
            maturity,
            "_Z",
            "XDC",
            "_T",
            "S",
            "V",
            "N",
            "_T",
        )
    )


def cell_map(report: dict[str, object]) -> dict[tuple[str, str, str], float]:
    result = {}
    for cell in report["cells"]:
        value = cell["canonical_value_million_RON"]
        if value is not None:
            result[(cell["measure"], cell["holder"], cell["issuer"])] = float(value)
    return result


def compare(name: str, observed: float | None, reconstructed: float | None) -> dict[str, object]:
    if observed is None or reconstructed is None:
        return {
            "name": name,
            "observed_million_RON": observed,
            "reconstructed_million_RON": reconstructed,
            "residual_million_RON": None,
            "status": "UNRESOLVED",
        }

    residual = reconstructed - observed
    return {
        "name": name,
        "observed_million_RON": observed,
        "reconstructed_million_RON": reconstructed,
        "residual_million_RON": residual,
        "absolute_tolerance_million_RON": ABS_TOLERANCE_MILLION_RON,
        "status": "PASS" if abs(residual) <= ABS_TOLERANCE_MILLION_RON else "FAIL",
    }


def main() -> None:
    coverage_path = OUT / "qsa_f3_coverage_audit.json"
    if not coverage_path.is_file():
        raise SystemExit("Run audit_qsa_accounting_coverage.py first")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    cells = cell_map(coverage)

    query_terms: list[Term] = []
    for measure in ("LE", "F"):
        for sector in RESIDENT_SECTORS:
            query_terms.extend(world_total_terms(sector, entry="A", measure=measure))
            query_terms.extend(world_total_terms(sector, entry="L", measure=measure))

        for entry in ("A", "L"):
            query_terms.append(
                Term(
                    1.0,
                    qsa_key(
                        counterpart_area="W1",
                        reference_sector="S1",
                        counterpart_sector="S1",
                        entry=entry,
                        measure=measure,
                    ),
                    f"W1_total_{entry}",
                )
            )

        for maturity in ("T", "S", "L"):
            query_terms.append(
                Term(
                    1.0,
                    qsa_key_maturity(
                        counterpart_area="W1",
                        reference_sector="S13",
                        counterpart_sector="S1",
                        entry="L",
                        measure=measure,
                        maturity=maturity,
                    ),
                    f"X_to_G_{maturity}",
                )
            )

    unique_keys = sorted({term.key for term in query_terms})
    series_by_key = {}
    for index, key in enumerate(unique_keys, start=1):
        print(f"[control {index}/{len(unique_keys)}] {key}", flush=True)
        series_by_key[key] = fetch_series(key)

    checks = []

    for measure_code, measure_name in (("LE", "stock"), ("F", "flow")):
        for sector in RESIDENT_SECTORS:
            asset_terms = world_total_terms(sector, entry="A", measure=measure_code)
            liability_terms = world_total_terms(sector, entry="L", measure=measure_code)

            asset_total, asset_detail = formula_value(
                asset_terms,
                series_by_key,
                measure=measure_code,
            )
            liability_total, liability_detail = formula_value(
                liability_terms,
                series_by_key,
                measure=measure_code,
            )

            row_values = [
                cells.get((measure_name, sector, issuer))
                for issuer in CANONICAL_SECTORS
            ]
            row_sum = (
                sum(value for value in row_values if value is not None)
                if all(value is not None for value in row_values)
                else None
            )

            column_values = [
                cells.get((measure_name, holder, sector))
                for holder in CANONICAL_SECTORS
            ]
            column_sum = (
                sum(value for value in column_values if value is not None)
                if all(value is not None for value in column_values)
                else None
            )

            asset_check = compare(
                f"{measure_name}:{sector}:row_assets_vs_W0",
                asset_total,
                row_sum,
            )
            asset_check["source_detail"] = asset_detail
            checks.append(asset_check)

            liability_check = compare(
                f"{measure_name}:{sector}:column_liabilities_vs_W0",
                liability_total,
                column_sum,
            )
            liability_check["source_detail"] = liability_detail
            checks.append(liability_check)

        external_asset_key = qsa_key(
            counterpart_area="W1",
            reference_sector="S1",
            counterpart_sector="S1",
            entry="A",
            measure=measure_code,
        )
        external_liability_key = qsa_key(
            counterpart_area="W1",
            reference_sector="S1",
            counterpart_sector="S1",
            entry="L",
            measure=measure_code,
        )

        external_asset_total, external_asset_detail = formula_value(
            (Term(1.0, external_asset_key, "W1_total_assets"),),
            series_by_key,
            measure=measure_code,
        )
        external_liability_total, external_liability_detail = formula_value(
            (Term(1.0, external_liability_key, "W1_total_liabilities"),),
            series_by_key,
            measure=measure_code,
        )

        reconstructed_external_assets = sum(
            cells[(measure_name, sector, "X")]
            for sector in RESIDENT_SECTORS
        )
        reconstructed_external_liabilities = sum(
            cells[(measure_name, "X", sector)]
            for sector in RESIDENT_SECTORS
        )

        check = compare(
            f"{measure_name}:resident_assets_against_X_vs_W1_total",
            external_asset_total,
            reconstructed_external_assets,
        )
        check["source_detail"] = external_asset_detail
        checks.append(check)

        check = compare(
            f"{measure_name}:X_assets_against_residents_vs_W1_total",
            external_liability_total,
            reconstructed_external_liabilities,
        )
        check["source_detail"] = external_liability_detail
        checks.append(check)

        maturity_values = {}
        maturity_details = {}
        for maturity in ("T", "S", "L"):
            key = qsa_key_maturity(
                counterpart_area="W1",
                reference_sector="S13",
                counterpart_sector="S1",
                entry="L",
                measure=measure_code,
                maturity=maturity,
            )
            value, detail = formula_value(
                (Term(1.0, key, f"X_to_G_{maturity}"),),
                series_by_key,
                measure=measure_code,
            )
            maturity_values[maturity] = value
            maturity_details[maturity] = detail

        reconstructed_maturity = (
            maturity_values["S"] + maturity_values["L"]
            if maturity_values["S"] is not None and maturity_values["L"] is not None
            else None
        )
        check = compare(
            f"{measure_name}:X_to_G_all_maturity_vs_short_plus_long",
            maturity_values["T"],
            reconstructed_maturity,
        )
        check["source_detail"] = maturity_details
        checks.append(check)

    status_counts = {}
    for check in checks:
        status = check["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    manifest = {
        "series": [series_by_key[key] for key in unique_keys],
    }
    report = {
        "audit_version": "0.1",
        "purpose": "Independent aggregate controls for the F3 bilateral source-coverage audit.",
        "absolute_tolerance_million_RON": ABS_TOLERANCE_MILLION_RON,
        "checks": checks,
        "status_counts": status_counts,
        "interpretation": {
            "PASS": "Published QSA aggregate and reconstructed canonical bilateral matrix agree within tolerance.",
            "UNRESOLVED": "A required published aggregate or canonical component is unavailable; do not promote affected cells.",
            "FAIL": "Published aggregate and reconstructed canonical matrix disagree beyond tolerance; treat as a blocker pending audit.",
        },
    }

    (OUT / "qsa_f3_control_series_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUT / "qsa_f3_reconciliation_controls.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"status_counts": status_counts}, indent=2))

    if status_counts.get("FAIL", 0) or status_counts.get("UNRESOLVED", 0):
        raise SystemExit(
            "F3 aggregate reconciliation gate did not fully pass; inspect qsa_f3_reconciliation_controls.json"
        )


if __name__ == "__main__":
    main()
