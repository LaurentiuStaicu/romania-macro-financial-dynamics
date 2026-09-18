from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

OUT = Path(os.environ.get("ACCOUNTING_AUDIT_OUT", "accounting_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub accounting source-coverage audit)"

CANONICAL_SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT_SECTORS = ("H", "C", "F", "G", "BNR")
DIRECT_SECTOR = {
    "H": "S1M",
    "C": "S11",
    "G": "S13",
    "BNR": "S121",
}
COMPOSITE_SECTOR = {
    "F": (("S12", 1.0), ("S121", -1.0)),
}

F3_INSTRUMENT = "F3"
AGGREGATE_ABS_TOLERANCE_MILLION_RON = 0.1


@dataclass(frozen=True)
class Term:
    coefficient: float
    key: str
    side: str


def sector_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in DIRECT_SECTOR:
        return ((DIRECT_SECTOR[sector], 1.0),)
    if sector in COMPOSITE_SECTOR:
        return COMPOSITE_SECTOR[sector]
    raise ValueError(
        f"Sector {sector} does not have a resident QSA reference-sector identity"
    )


def qsa_key(
    *,
    counterpart_area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
    measure: str,
    maturity: str = "T",
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
            F3_INSTRUMENT,
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


def formula(holder: str, issuer: str, *, side: str, measure: str) -> tuple[Term, ...]:
    if holder == "X" and issuer == "X":
        return ()

    if holder == "X":
        if side != "canonical":
            return ()
        return tuple(
            Term(
                issuer_coefficient,
                qsa_key(
                    counterpart_area="W1",
                    reference_sector=issuer_code,
                    counterpart_sector="S1",
                    entry="L",
                    measure=measure,
                ),
                "issuer_liability_to_nonresident",
            )
            for issuer_code, issuer_coefficient in sector_terms(issuer)
        )

    if issuer == "X":
        if side != "canonical":
            return ()
        return tuple(
            Term(
                holder_coefficient,
                qsa_key(
                    counterpart_area="W1",
                    reference_sector=holder_code,
                    counterpart_sector="S1",
                    entry="A",
                    measure=measure,
                ),
                "holder_asset_against_nonresident",
            )
            for holder_code, holder_coefficient in sector_terms(holder)
        )

    holder_components = sector_terms(holder)
    issuer_components = sector_terms(issuer)
    terms: list[Term] = []

    if side == "canonical":
        for holder_code, holder_coefficient in holder_components:
            for issuer_code, issuer_coefficient in issuer_components:
                terms.append(
                    Term(
                        holder_coefficient * issuer_coefficient,
                        qsa_key(
                            counterpart_area="W2",
                            reference_sector=holder_code,
                            counterpart_sector=issuer_code,
                            entry="A",
                            measure=measure,
                        ),
                        "asset",
                    )
                )
    elif side == "mirror":
        for issuer_code, issuer_coefficient in issuer_components:
            for holder_code, holder_coefficient in holder_components:
                terms.append(
                    Term(
                        holder_coefficient * issuer_coefficient,
                        qsa_key(
                            counterpart_area="W2",
                            reference_sector=issuer_code,
                            counterpart_sector=holder_code,
                            entry="L",
                            measure=measure,
                        ),
                        "liability_mirror",
                    )
                )
    else:
        raise ValueError(side)

    return tuple(terms)


def aggregate_formula(sector: str, *, entry: str, measure: str) -> tuple[Term, ...]:
    if sector == "X":
        raise ValueError("Rest-of-world totals are derived from resident counterpart positions")
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
            "published_total",
        )
        for code, coefficient in sector_terms(sector)
    )


def maturity_control_terms(*, measure: str, maturity: str) -> tuple[Term, ...]:
    return (
        Term(
            1.0,
            qsa_key(
                counterpart_area="W1",
                reference_sector="S13",
                counterpart_sector="S1",
                entry="L",
                measure=measure,
                maturity=maturity,
            ),
            f"X_to_G_{maturity}",
        ),
    )


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_series(key: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "startPeriod": "2025-Q1",
            "endPeriod": "2025-Q4",
            "format": "csvdata",
        }
    )
    url = f"{API}{key}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            status = int(response.status)
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = int(exc.code)
        headers = dict(exc.headers.items())
    except urllib.error.URLError as exc:
        return {
            "key": key,
            "url": url,
            "status": "NETWORK_ERROR",
            "error": str(exc),
            "rows": [],
        }

    raw_name = f"{sha256(key.encode('utf-8'))[:16]}.raw"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_bytes": len(body),
        "raw_sha256": sha256(body),
        "content_type": headers.get("Content-Type"),
        "last_modified": headers.get("Last-Modified"),
        "etag": headers.get("ETag"),
        "rows": [],
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result

    try:
        text = body.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = repr(exc)
        return result

    parsed = []
    for row in rows:
        period = row.get("TIME_PERIOD")
        value = row.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue

        decimals_raw = row.get("DECIMALS")
        try:
            decimals = int(decimals_raw) if decimals_raw not in (None, "") else None
        except ValueError:
            decimals = None

        parsed.append(
            {
                "period": period,
                "value_raw": numeric,
                "value_published_precision": (
                    round(numeric, decimals) if decimals is not None else numeric
                ),
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "obs_status": row.get("OBS_STATUS"),
                "decimals": decimals,
            }
        )

    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    result["unit_values"] = sorted({str(row["unit"]) for row in parsed})
    result["unit_mult_values"] = sorted({str(row["unit_mult"]) for row in parsed})
    result["decimal_values"] = sorted(
        {str(row["decimals"]) for row in parsed if row["decimals"] is not None}
    )
    return result


def required_period_value(
    series: dict[str, object],
    period: str,
    *,
    published_precision: bool,
) -> float | None:
    field = "value_published_precision" if published_precision else "value_raw"
    for row in series.get("rows", []):
        if row["period"] == period and math.isfinite(float(row[field])):
            return float(row[field])
    return None


def formula_value(
    terms: Iterable[Term],
    series_by_key: dict[str, dict[str, object]],
    *,
    measure: str,
    published_precision: bool = True,
) -> tuple[float | None, dict[str, object]]:
    terms = tuple(terms)
    if not terms:
        return None, {"status": "OUTSIDE_BOUNDARY"}

    required_periods = (
        ("2025-Q4",)
        if measure == "LE"
        else ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    )

    components = []
    total = 0.0
    for term in terms:
        series = series_by_key[term.key]
        values = [
            required_period_value(
                series,
                period,
                published_precision=published_precision,
            )
            for period in required_periods
        ]
        available = (
            series.get("status") == "AVAILABLE"
            and all(value is not None for value in values)
            and series.get("unit_values") == ["XDC"]
            and series.get("unit_mult_values") == ["6"]
        )
        components.append(
            {
                "coefficient": term.coefficient,
                "key": term.key,
                "side": term.side,
                "series_status": series.get("status"),
                "period_values": dict(zip(required_periods, values)),
                "unit_values": series.get("unit_values"),
                "unit_mult_values": series.get("unit_mult_values"),
                "decimal_values": series.get("decimal_values"),
                "definitionally_usable": available,
            }
        )
        if not available:
            return None, {
                "status": "UNRESOLVED_COMPONENT",
                "components": components,
            }

        component_value = (
            float(values[0])
            if measure == "LE"
            else sum(float(value) for value in values if value is not None)
        )
        total += term.coefficient * component_value

    return total, {
        "status": "EXACT_QSA_OR_EXACT_AGGREGATION",
        "components": components,
        "published_precision": published_precision,
    }


def reconciliation_status(residual: float | None) -> str:
    if residual is None:
        return "UNRESOLVED"
    if abs(residual) <= AGGREGATE_ABS_TOLERANCE_MILLION_RON:
        return "PASS"
    return "MISMATCH_REQUIRES_AUDIT"


def main() -> None:
    plans = []
    unique_keys: set[str] = set()

    for measure in ("LE", "F"):
        for holder in CANONICAL_SECTORS:
            for issuer in CANONICAL_SECTORS:
                canonical = formula(holder, issuer, side="canonical", measure=measure)
                mirror = formula(holder, issuer, side="mirror", measure=measure)
                plans.append(
                    {
                        "instrument": "F3",
                        "measure": "stock" if measure == "LE" else "flow",
                        "qsa_measure": measure,
                        "holder": holder,
                        "issuer": issuer,
                        "canonical_terms": [term.__dict__ for term in canonical],
                        "mirror_terms": [term.__dict__ for term in mirror],
                    }
                )
                unique_keys.update(term.key for term in canonical)
                unique_keys.update(term.key for term in mirror)

        for sector in RESIDENT_SECTORS:
            for entry in ("A", "L"):
                unique_keys.update(
                    term.key
                    for term in aggregate_formula(sector, entry=entry, measure=measure)
                )

        for maturity in ("S", "L"):
            unique_keys.update(
                term.key
                for term in maturity_control_terms(
                    measure=measure,
                    maturity=maturity,
                )
            )

    series_by_key: dict[str, dict[str, object]] = {}
    for index, key in enumerate(sorted(unique_keys), start=1):
        print(f"[{index}/{len(unique_keys)}] {key}", flush=True)
        series_by_key[key] = fetch_series(key)

    results = []
    status_counts: dict[str, int] = {}

    for plan in plans:
        measure = str(plan["qsa_measure"])
        canonical_terms = tuple(Term(**term) for term in plan["canonical_terms"])
        mirror_terms = tuple(Term(**term) for term in plan["mirror_terms"])

        canonical_value, canonical_detail = formula_value(
            canonical_terms,
            series_by_key,
            measure=measure,
        )
        mirror_value, mirror_detail = formula_value(
            mirror_terms,
            series_by_key,
            measure=measure,
        )

        if plan["holder"] == "X" and plan["issuer"] == "X":
            status = "OUTSIDE_BOUNDARY_CANDIDATE_NOT_APPLICABLE"
            residual = None
        elif canonical_value is None:
            status = "UNRESOLVED_SOURCE_COVERAGE"
            residual = None
        elif mirror_terms and mirror_value is None:
            status = "OBSERVABLE_CANONICAL_MIRROR_UNAVAILABLE"
            residual = None
        elif mirror_terms:
            residual = canonical_value - float(mirror_value)
            status = (
                "OBSERVABLE_MIRROR_RECONCILED"
                if abs(residual) <= AGGREGATE_ABS_TOLERANCE_MILLION_RON
                else "MIRROR_MISMATCH_REQUIRES_AUDIT"
            )
        else:
            residual = None
            status = "OBSERVABLE_NONRESIDENT_BOUNDARY"

        status_counts[status] = status_counts.get(status, 0) + 1
        results.append(
            {
                **plan,
                "canonical_value_million_RON": canonical_value,
                "mirror_value_million_RON": mirror_value,
                "mirror_residual_million_RON": residual,
                "status": status,
                "canonical_detail": canonical_detail,
                "mirror_detail": mirror_detail,
            }
        )

    cells_by_measure = {
        measure: {
            (item["holder"], item["issuer"]): item
            for item in results
            if item["qsa_measure"] == measure
        }
        for measure in ("LE", "F")
    }

    aggregate_controls = []
    for measure in ("LE", "F"):
        matrix = cells_by_measure[measure]
        for sector in RESIDENT_SECTORS:
            row_values = [
                matrix[(sector, issuer)]["canonical_value_million_RON"]
                for issuer in CANONICAL_SECTORS
            ]
            column_values = [
                matrix[(holder, sector)]["canonical_value_million_RON"]
                for holder in CANONICAL_SECTORS
            ]

            row_sum = (
                sum(float(value) for value in row_values if value is not None)
                if all(value is not None for value in row_values)
                else None
            )
            column_sum = (
                sum(float(value) for value in column_values if value is not None)
                if all(value is not None for value in column_values)
                else None
            )

            published_assets, assets_detail = formula_value(
                aggregate_formula(sector, entry="A", measure=measure),
                series_by_key,
                measure=measure,
            )
            published_liabilities, liabilities_detail = formula_value(
                aggregate_formula(sector, entry="L", measure=measure),
                series_by_key,
                measure=measure,
            )

            asset_residual = (
                row_sum - published_assets
                if row_sum is not None and published_assets is not None
                else None
            )
            liability_residual = (
                column_sum - published_liabilities
                if column_sum is not None and published_liabilities is not None
                else None
            )

            aggregate_controls.append(
                {
                    "measure": "stock" if measure == "LE" else "flow",
                    "qsa_measure": measure,
                    "sector": sector,
                    "canonical_row_sum_million_RON": row_sum,
                    "published_total_assets_million_RON": published_assets,
                    "asset_residual_million_RON": asset_residual,
                    "asset_reconciliation": reconciliation_status(asset_residual),
                    "canonical_column_sum_million_RON": column_sum,
                    "published_total_liabilities_million_RON": published_liabilities,
                    "liability_residual_million_RON": liability_residual,
                    "liability_reconciliation": reconciliation_status(liability_residual),
                    "published_assets_detail": assets_detail,
                    "published_liabilities_detail": liabilities_detail,
                }
            )

    maturity_controls = []
    for measure in ("LE", "F"):
        matrix = cells_by_measure[measure]
        all_maturity = matrix[("X", "G")]["canonical_value_million_RON"]
        short_value, short_detail = formula_value(
            maturity_control_terms(measure=measure, maturity="S"),
            series_by_key,
            measure=measure,
        )
        long_value, long_detail = formula_value(
            maturity_control_terms(measure=measure, maturity="L"),
            series_by_key,
            measure=measure,
        )
        component_sum = (
            short_value + long_value
            if short_value is not None and long_value is not None
            else None
        )
        residual = (
            all_maturity - component_sum
            if all_maturity is not None and component_sum is not None
            else None
        )
        maturity_controls.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "cell": "X->G",
                "all_maturity_million_RON": all_maturity,
                "short_maturity_million_RON": short_value,
                "long_maturity_million_RON": long_value,
                "short_plus_long_million_RON": component_sum,
                "residual_million_RON": residual,
                "reconciliation": reconciliation_status(residual),
                "short_detail": short_detail,
                "long_detail": long_detail,
            }
        )

    aggregate_status_counts: dict[str, int] = {}
    for control in aggregate_controls:
        for field in ("asset_reconciliation", "liability_reconciliation"):
            status = str(control[field])
            aggregate_status_counts[status] = aggregate_status_counts.get(status, 0) + 1

    maturity_status_counts: dict[str, int] = {}
    for control in maturity_controls:
        status = str(control["reconciliation"])
        maturity_status_counts[status] = maturity_status_counts.get(status, 0) + 1

    report = {
        "audit_version": "0.2",
        "purpose": "Non-mutating source-coverage and aggregate-reconciliation audit for the first-priority F3 Accounting Spine matrices.",
        "benchmark": {
            "stock_period": "2025-Q4",
            "flow_period": "2025-Q1..2025-Q4",
        },
        "rules": {
            "benchmark_changed": False,
            "synthetic_allocation": False,
            "aggregate_absolute_tolerance_million_RON": AGGREGATE_ABS_TOLERANCE_MILLION_RON,
            "required_unit": "XDC",
            "required_unit_multiplier": "6",
            "stored_value_candidate": "OBS_VALUE rounded to the official DECIMALS attribute; raw OBS_VALUE is retained in provenance",
        },
        "series_requested": len(unique_keys),
        "series_status_counts": {},
        "cell_status_counts": status_counts,
        "aggregate_reconciliation_status_counts": aggregate_status_counts,
        "maturity_reconciliation_status_counts": maturity_status_counts,
        "cells": results,
        "aggregate_controls": aggregate_controls,
        "maturity_controls": maturity_controls,
    }

    for series in series_by_key.values():
        status = str(series.get("status"))
        report["series_status_counts"][status] = (
            report["series_status_counts"].get(status, 0) + 1
        )

    (OUT / "qsa_f3_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUT / "qsa_f3_series_manifest.json").write_text(
        json.dumps(
            {"series": [series_by_key[key] for key in sorted(series_by_key)]},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with (OUT / "qsa_f3_cell_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "measure",
                "holder",
                "issuer",
                "status",
                "canonical_value_million_RON",
                "mirror_value_million_RON",
                "mirror_residual_million_RON",
            ]
        )
        for item in results:
            writer.writerow(
                [
                    item["measure"],
                    item["holder"],
                    item["issuer"],
                    item["status"],
                    item["canonical_value_million_RON"],
                    item["mirror_value_million_RON"],
                    item["mirror_residual_million_RON"],
                ]
            )

    print(
        json.dumps(
            {
                "series_requested": len(unique_keys),
                "series_status_counts": report["series_status_counts"],
                "cell_status_counts": status_counts,
                "aggregate_reconciliation_status_counts": aggregate_status_counts,
                "maturity_reconciliation_status_counts": maturity_status_counts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
