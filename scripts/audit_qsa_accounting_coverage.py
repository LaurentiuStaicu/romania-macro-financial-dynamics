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
MIRROR_ABS_TOLERANCE_MILLION_RON = 0.02


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
    raise ValueError(f"Sector {sector} does not have a resident QSA reference-sector identity")


def qsa_key(
    *,
    counterpart_area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
    measure: str,
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
            "T",
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
        parsed.append(
            {
                "period": period,
                "value": numeric,
                "unit": row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "obs_status": row.get("OBS_STATUS"),
                "decimals": row.get("DECIMALS"),
            }
        )

    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    result["unit_values"] = sorted({str(row["unit"]) for row in parsed})
    result["unit_mult_values"] = sorted({str(row["unit_mult"]) for row in parsed})
    return result


def required_period_value(series: dict[str, object], period: str) -> float | None:
    for row in series.get("rows", []):
        if row["period"] == period and math.isfinite(float(row["value"])):
            return float(row["value"])
    return None


def formula_value(
    terms: Iterable[Term],
    series_by_key: dict[str, dict[str, object]],
    *,
    measure: str,
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
        values = [required_period_value(series, period) for period in required_periods]
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
    }


def main() -> None:
    plans = []
    unique_keys: set[str] = set()

    for measure in ("LE", "F"):
        for holder in CANONICAL_SECTORS:
            for issuer in CANONICAL_SECTORS:
                canonical = formula(holder, issuer, side="canonical", measure=measure)
                mirror = formula(holder, issuer, side="mirror", measure=measure)
                plan = {
                    "instrument": "F3",
                    "measure": "stock" if measure == "LE" else "flow",
                    "qsa_measure": measure,
                    "holder": holder,
                    "issuer": issuer,
                    "canonical_terms": [term.__dict__ for term in canonical],
                    "mirror_terms": [term.__dict__ for term in mirror],
                }
                plans.append(plan)
                unique_keys.update(term.key for term in canonical)
                unique_keys.update(term.key for term in mirror)

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
            canonical_terms, series_by_key, measure=measure
        )
        mirror_value, mirror_detail = formula_value(
            mirror_terms, series_by_key, measure=measure
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
                if abs(residual) <= MIRROR_ABS_TOLERANCE_MILLION_RON
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

    report = {
        "audit_version": "0.1",
        "purpose": "Non-mutating source-coverage audit for the first-priority F3 Accounting Spine matrices.",
        "benchmark": {
            "stock_period": "2025-Q4",
            "flow_period": "2025-Q1..2025-Q4",
        },
        "rules": {
            "benchmark_changed": false,
            "synthetic_allocation": false,
            "mirror_absolute_tolerance_million_RON": MIRROR_ABS_TOLERANCE_MILLION_RON,
            "required_unit": "XDC",
            "required_unit_multiplier": "6",
        },
        "series_requested": len(unique_keys),
        "series_status_counts": {},
        "cell_status_counts": status_counts,
        "cells": results,
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
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
