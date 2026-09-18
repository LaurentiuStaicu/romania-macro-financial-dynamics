from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
MATURITIES = ("T", "S", "L")
TOL = 0.1
API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F4 Phase B rank audit)"


def qsa_key(entry: str, measure: str, maturity: str) -> str:
    return ".".join(
        (
            "Q", "N", "RO", "W1", "S1", "S1", "N", entry, measure,
            "F4", maturity, "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str, out: Path) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {"startPeriod": "2025-Q1", "endPeriod": "2025-Q4", "format": "csvdata"}
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"}
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                status = int(response.status)
                headers = dict(response.headers.items())
            break
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            headers = dict(exc.headers.items())
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                return {
                    "key": series_key,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "rows": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = out / "raw" / f"{sha256(series_key.encode())[:16]}.raw"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)
    result: dict[str, object] = {
        "key": series_key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(out)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "content_type": headers.get("Content-Type"),
        "rows": [],
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result

    parsed = []
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        period = row.get("TIME_PERIOD")
        raw_value = row.get("OBS_VALUE")
        if not period or raw_value in (None, ""):
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        parsed.append(
            {
                "period": period,
                "value": value,
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "instrument": row.get("INSTR_ASSET"),
                "entry": row.get("ACCOUNTING_ENTRY"),
                "measure": row.get("STO"),
                "maturity": row.get("MATURITY"),
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def series_value(series: dict[str, object], measure: str, maturity: str) -> float | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != "F4"
        or row.get("maturity") != maturity
        for row in rows
    ):
        return None
    needed = (
        ("2025-Q4",)
        if measure == "LE"
        else ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    )
    mapping = {str(row["period"]): float(row["value"]) for row in rows}
    if not all(p in mapping and math.isfinite(mapping[p]) for p in needed):
        return None
    return mapping[needed[0]] if measure == "LE" else sum(mapping[p] for p in needed)


def select_maturity(values: dict[str, float | None]) -> dict[str, object]:
    direct = values["T"]
    short = values["S"]
    long = values["L"]
    residual = (
        None
        if direct is None or short is None or long is None
        else float(direct) - float(short) - float(long)
    )
    control = (
        "CONTROL_UNAVAILABLE"
        if residual is None
        else "PASS"
        if abs(residual) <= TOL
        else "FAIL"
    )
    if direct is not None and control != "FAIL":
        selected = float(direct)
        derivation = "DIRECT_T"
    elif direct is None and short is not None and long is not None:
        selected = float(short) + float(long)
        derivation = "EXACT_S_PLUS_L"
    else:
        selected = None
        derivation = "UNAVAILABLE"
    return {
        "selected_value": selected,
        "derivation": derivation,
        "maturity_values": values,
        "maturity_residual_T_minus_S_minus_L": residual,
        "maturity_control_status": control,
    }


def term_component(term: dict[str, object], measure: str) -> float | None:
    if not term.get("usable"):
        return None
    vals = term.get("values")
    if not isinstance(vals, list) or not vals:
        return None
    return float(vals[0]) if measure == "stock" else sum(float(v) for v in vals)


def s12_holder_combined(cell: dict[str, object]) -> dict[str, object]:
    measure = str(cell["measure"])
    orientation_name = (
        "holder_asset_W1" if cell["issuer"] == "X" else "holder_asset_W2"
    )
    orientation = cell.get("orientations", {}).get(orientation_name)
    if not orientation:
        return {"selected_value": None, "derivation": "UNAVAILABLE"}

    by_maturity: dict[str, float | None] = {}
    for maturity in MATURITIES:
        term_pack = orientation["terms"][maturity]["terms"]
        selected_terms = []
        for term in term_pack:
            parts = str(term["key"]).split(".")
            if len(parts) > 5 and parts[4] == "S12":
                selected_terms.append(term)
        if not selected_terms:
            by_maturity[maturity] = None
            continue
        components = [term_component(t, measure) for t in selected_terms]
        if any(v is None for v in components):
            by_maturity[maturity] = None
        else:
            by_maturity[maturity] = sum(
                float(t["coefficient"]) * float(v)
                for t, v in zip(selected_terms, components)
            )
    return select_maturity(by_maturity)


def direct_s12_issuer_component(cell: dict[str, object]) -> dict[str, object]:
    measure = str(cell["measure"])
    orientation = cell.get("orientations", {}).get("holder_asset_W2")
    if not orientation:
        return {"selected_value": None, "derivation": "UNAVAILABLE"}
    by_maturity: dict[str, float | None] = {}
    for maturity in MATURITIES:
        terms = orientation["terms"][maturity]["terms"]
        selected = []
        for term in terms:
            parts = str(term["key"]).split(".")
            if len(parts) > 5 and parts[5] == "S12":
                selected.append(term)
        if not selected:
            by_maturity[maturity] = None
            continue
        comps = [term_component(t, measure) for t in selected]
        if any(v is None for v in comps):
            by_maturity[maturity] = None
        else:
            by_maturity[maturity] = sum(
                float(t["coefficient"]) * float(v)
                for t, v in zip(selected, comps)
            )
    return select_maturity(by_maturity)


def variables() -> list[tuple[str, str]]:
    return [
        (holder, issuer)
        for holder in SECTORS
        for issuer in SECTORS
        if not (holder == "X" and issuer == "X")
    ]


def rref_and_nullspace(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> tuple[int, list[list[Fraction]]]:
    if not equations:
        return 0, [
            [Fraction(1 if i == j else 0) for i in range(len(vars_))]
            for j in range(len(vars_))
        ]
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


def unique_variables(
    equations: list[dict[tuple[str, str], int]],
    vars_: list[tuple[str, str]],
) -> dict[str, object]:
    rank, nullspace = rref_and_nullspace(equations, vars_)
    unique = []
    nonunique = []
    for i, var in enumerate(vars_):
        if all(vec[i] == 0 for vec in nullspace):
            unique.append(f"{var[0]}→{var[1]}")
        else:
            nonunique.append(f"{var[0]}→{var[1]}")
    return {
        "variables": len(vars_),
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
        default=Path("f4_phase_a_artifacts/f4_loans_coverage_audit.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(os.environ.get("F4_PHASE_B_OUT", "f4_phase_b_artifacts")),
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    phase_a = json.loads(args.phase_a_report.read_text(encoding="utf-8"))
    if phase_a["instrument"] != "F4":
        raise RuntimeError("Phase A artifact is not F4")
    if phase_a["network_errors_present"]:
        raise RuntimeError("Phase A has network errors; Phase B source claims blocked")
    if phase_a["maturity_conflict_count"] != 0:
        raise RuntimeError("Phase A maturity conflicts block Phase B")

    required = {
        qsa_key(entry, measure, maturity)
        for entry in ("A", "L")
        for measure in ("LE", "F")
        for maturity in MATURITIES
    }
    controls_by_key = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch, key, args.out): key for key in sorted(required)}
        for i, future in enumerate(as_completed(futures), start=1):
            key = futures[future]
            controls_by_key[key] = future.result()
            print(f"[W1 {i}/{len(futures)}] {key}", flush=True)

    w1_controls = {}
    for measure_code, label in (("LE", "stock"), ("F", "flow")):
        for entry, kind in (("A", "assets"), ("L", "liabilities")):
            maturity_values = {
                maturity: series_value(
                    controls_by_key[qsa_key(entry, measure_code, maturity)],
                    measure_code,
                    maturity,
                )
                for maturity in MATURITIES
            }
            w1_controls[(label, kind)] = select_maturity(maturity_values)

    vars_ = variables()
    phase_a_cells = {
        (c["measure"], c["holder"], c["issuer"]): c
        for c in phase_a["cells"]
    }
    aggregate = {
        (r["measure"], r["kind"], r["sector"]): r
        for r in phase_a["aggregate_reconciliation"]
    }

    analyses = {}
    explicit_derivations = {"stock": [], "flow": []}
    combined_s12 = {"stock": {}, "flow": {}}

    for measure in ("stock", "flow"):
        equations: list[dict[tuple[str, str], int]] = []
        equation_labels: list[str] = []

        def add(coeffs: dict[tuple[str, str], int], label: str) -> None:
            equations.append(coeffs)
            equation_labels.append(label)

        for cell in phase_a["cells"]:
            if cell["measure"] != measure:
                continue
            if cell["status"] == "OBSERVABLE_OR_EXACT_DERIVATION":
                add(
                    {(cell["holder"], cell["issuer"]): 1},
                    f"direct:{cell['holder']}→{cell['issuer']}",
                )

        for sector in RESIDENT:
            holder_control = aggregate[(measure, "holder_total", sector)]
            issuer_control = aggregate[(measure, "issuer_total", sector)]
            if holder_control["official_aggregate_million_RON"] is not None:
                add(
                    {
                        (sector, issuer): 1
                        for issuer in SECTORS
                        if not (sector == "X" and issuer == "X")
                    },
                    f"W0-holder:{sector}",
                )
            if issuer_control["official_aggregate_million_RON"] is not None:
                add(
                    {
                        (holder, sector): 1
                        for holder in SECTORS
                        if not (holder == "X" and sector == "X")
                    },
                    f"W0-issuer:{sector}",
                )

        for issuer in ("H", "C", "F", "G", "X", "BNR"):
            cell = phase_a_cells[(measure, "F", issuer)]
            combined = s12_holder_combined(cell)
            combined_s12[measure][issuer] = combined
            if combined["selected_value"] is not None:
                add(
                    {("F", issuer): 1, ("BNR", issuer): 1},
                    f"S12-holder:{issuer}",
                )

        w1_asset = w1_controls[(measure, "assets")]
        if w1_asset["selected_value"] is not None:
            add(
                {(holder, "X"): 1 for holder in RESIDENT},
                "W1-total-assets",
            )
        w1_liab = w1_controls[(measure, "liabilities")]
        if w1_liab["selected_value"] is not None:
            add(
                {("X", issuer): 1 for issuer in RESIDENT},
                "W1-total-liabilities",
            )

        base_identification = unique_variables(equations, vars_)
        stock_zero_condition = False
        structural_equations = list(equations)
        structural_labels = list(equation_labels)

        if measure == "stock":
            bnr_control = aggregate[(measure, "issuer_total", "BNR")]
            bnr_maturity = bnr_control["aggregate_maturity"]
            stock_zero_condition = (
                bnr_control["official_aggregate_million_RON"] is not None
                and abs(float(bnr_control["official_aggregate_million_RON"])) <= TOL
                and bnr_maturity["selected_value"] is not None
                and abs(float(bnr_maturity["selected_value"])) <= TOL
                and bnr_maturity["maturity_control_status"] != "FAIL"
            )
            if stock_zero_condition:
                for holder in SECTORS:
                    if holder == "X" or holder in RESIDENT:
                        structural_equations.append({(holder, "BNR"): 1})
                        structural_labels.append(f"conditional-BNR-issuer-zero:{holder}")

        structural_identification = unique_variables(structural_equations, vars_)

        if measure == "stock" and stock_zero_condition:
            for holder in ("H", "C", "G"):
                row_total = float(
                    aggregate[(measure, "holder_total", holder)][
                        "official_aggregate_million_RON"
                    ]
                )
                known = 0.0
                source_cells = []
                complete = True
                for issuer in ("H", "C", "G", "X"):
                    c = phase_a_cells[(measure, holder, issuer)]
                    if c["value_million_RON"] is None:
                        complete = False
                        break
                    known += float(c["value_million_RON"])
                    source_cells.append(f"{holder}→{issuer}")
                if complete:
                    value = row_total - known
                    source_check = direct_s12_issuer_component(
                        phase_a_cells[(measure, holder, "F")]
                    )
                    residual = (
                        None
                        if source_check["selected_value"] is None
                        else value - float(source_check["selected_value"])
                    )
                    explicit_derivations[measure].append(
                        {
                            "cell": f"{holder}→F",
                            "method": "W0 holder-row complement with conditional BNR issuer stock zero",
                            "value_million_RON": value,
                            "independent_S12_asset_value_million_RON":
                                source_check["selected_value"],
                            "independent_residual_million_RON": residual,
                            "status": (
                                "PASS"
                                if residual is not None and abs(residual) <= TOL
                                else "CONTROL_UNAVAILABLE"
                                if residual is None
                                else "FAIL"
                            ),
                        }
                    )

        for issuer in ("H", "C", "G"):
            issuer_total = aggregate[(measure, "issuer_total", issuer)][
                "official_aggregate_million_RON"
            ]
            combined = combined_s12[measure][issuer]["selected_value"]
            direct_hcg = []
            if issuer_total is not None and combined is not None:
                complete = True
                subtotal = 0.0
                for holder in ("H", "C", "G"):
                    c = phase_a_cells[(measure, holder, issuer)]
                    if c["value_million_RON"] is None:
                        complete = False
                        break
                    subtotal += float(c["value_million_RON"])
                    direct_hcg.append(f"{holder}→{issuer}")
                if complete:
                    value = float(issuer_total) - subtotal - float(combined)
                    explicit_derivations[measure].append(
                        {
                            "cell": f"X→{issuer}",
                            "method": "W0 issuer-column complement using exact S12=(F+BNR) holder aggregate",
                            "value_million_RON": value,
                            "status": "EXACT_COMPLEMENT_CANDIDATE",
                        }
                    )

        if measure == "stock" and stock_zero_condition:
            derived_map = {
                item["cell"]: item["value_million_RON"]
                for item in explicit_derivations[measure]
            }
            w1_liab_value = w1_controls[(measure, "liabilities")]["selected_value"]
            if (
                w1_liab_value is not None
                and all(f"X→{j}" in derived_map for j in ("H", "C", "G"))
            ):
                xf = float(w1_liab_value) - sum(
                    float(derived_map[f"X→{j}"]) for j in ("H", "C", "G")
                )
                explicit_derivations[measure].append(
                    {
                        "cell": "X→F",
                        "method": "W1 total-liability complement after X→H/C/G and conditional X→BNR=0",
                        "value_million_RON": xf,
                        "status": "EXACT_COMPLEMENT_CANDIDATE",
                    }
                )
            for holder in SECTORS:
                explicit_derivations[measure].append(
                    {
                        "cell": f"{holder}→BNR",
                        "method": "conditional stock partition-zero from published BNR W0 F4 liabilities=0",
                        "value_million_RON": 0.0,
                        "status": "CONDITIONAL_STRUCTURAL_ZERO",
                    }
                )

        unique_set = set(
            structural_identification["unique_cells"]
            if measure == "stock"
            else base_identification["unique_cells"]
        )
        for item in explicit_derivations[measure]:
            item["rank_uniqueness_confirmed"] = item["cell"] in unique_set

        external_asset_sum = None
        external_asset_residual = None
        if all(
            phase_a_cells[(measure, h, "X")]["value_million_RON"] is not None
            for h in ("H", "C", "G")
        ) and combined_s12[measure]["X"]["selected_value"] is not None:
            external_asset_sum = sum(
                float(phase_a_cells[(measure, h, "X")]["value_million_RON"])
                for h in ("H", "C", "G")
            ) + float(combined_s12[measure]["X"]["selected_value"])
            if w1_asset["selected_value"] is not None:
                external_asset_residual = (
                    external_asset_sum - float(w1_asset["selected_value"])
                )

        derived_external_liab = {
            item["cell"]: item["value_million_RON"]
            for item in explicit_derivations[measure]
            if item["cell"].startswith("X→")
            and item["rank_uniqueness_confirmed"]
        }
        external_liability_sum = None
        external_liability_residual = None
        required_external = {f"X→{i}" for i in RESIDENT}
        if required_external.issubset(derived_external_liab):
            external_liability_sum = sum(
                float(derived_external_liab[f"X→{i}"]) for i in RESIDENT
            )
            if w1_liab["selected_value"] is not None:
                external_liability_residual = (
                    external_liability_sum - float(w1_liab["selected_value"])
                )

        analyses[measure] = {
            "equation_count_before_structural_zero": len(equations),
            "equation_labels_before_structural_zero": equation_labels,
            "identification_before_structural_zero": base_identification,
            "stock_BNR_zero_condition_pass": stock_zero_condition,
            "equation_count_with_stock_BNR_zero":
                len(structural_equations) if measure == "stock" else None,
            "identification_with_stock_BNR_zero":
                structural_identification if measure == "stock" else None,
            "W1_asset_control": w1_asset,
            "W1_liability_control": w1_liab,
            "external_asset_sum_from_resolved_plus_S12_million_RON":
                external_asset_sum,
            "external_asset_vs_W1_residual_million_RON":
                external_asset_residual,
            "external_liability_sum_if_fully_unique_million_RON":
                external_liability_sum,
            "external_liability_vs_W1_residual_million_RON":
                external_liability_residual,
            "S12_holder_combined": combined_s12[measure],
        }

    w1_status_counts = {}
    for series in controls_by_key.values():
        status = str(series.get("status"))
        w1_status_counts[status] = w1_status_counts.get(status, 0) + 1

    report = {
        "audit_version": "0.1",
        "instrument": "F4",
        "phase": "exact aggregate-complement and rank audit",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "phase_A_summary": {
            "series_requested": phase_a["series_requested"],
            "series_status_counts": phase_a["series_status_counts"],
            "cell_status_counts": phase_a["cell_status_counts"],
            "maturity_conflict_count": phase_a["maturity_conflict_count"],
        },
        "W1_control_series_status_counts": w1_status_counts,
        "W1_network_errors_present": any(
            x.get("status") == "NETWORK_ERROR" for x in controls_by_key.values()
        ),
        "analyses": analyses,
        "explicit_derivation_candidates": explicit_derivations,
        "stock_remaining_boundary": (
            "Under the explicit BNR issuer-zero stock scenario, any remaining "
            "non-unique stock cells must remain unresolved; in particular the "
            "6.1 million RON BNR asset row may not be allocated across counterparts."
        ),
        "flow_boundary": (
            "Zero aggregate BNR F4 transactions are not converted into bilateral "
            "zero-flow equations. Flow uniqueness is determined only by published "
            "direct cells, W0/W1 controls and exact S12=F+BNR holder identities."
        ),
    }

    (args.out / "f4_exact_complement_rank_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "stock": analyses["stock"][
                    "identification_with_stock_BNR_zero"
                ],
                "flow": analyses["flow"][
                    "identification_before_structural_zero"
                ],
                "stock_external_asset_residual":
                    analyses["stock"]["external_asset_vs_W1_residual_million_RON"],
                "flow_external_asset_residual":
                    analyses["flow"]["external_asset_vs_W1_residual_million_RON"],
                "W1_control_series_status_counts": w1_status_counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
