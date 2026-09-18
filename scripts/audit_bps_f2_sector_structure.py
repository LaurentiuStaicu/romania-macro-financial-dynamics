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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(os.environ.get("BPS_F2_AUDIT_OUT", "bps_f2_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/BPS/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub BPS F2 sector audit)"

SECTORS = (
    "S1", "S121", "S12T", "S122", "S123", "S13", "S1P",
    "S12M", "S124", "S12Q", "S12O", "S1V", "S11", "S1M",
)
MEASURES = ("LE", "T")
UNITS = ("EUR", "RON")
MATURITIES = ("T", "S", "L")
TOL = 0.1


def key(sector: str, measure: str, maturity: str, unit: str) -> str:
    return ".".join(
        (
            "Q", "N", "RO", "W1", sector, "S1", measure, "A",
            "FA", "O", "F2", maturity, unit, "_T", "N", "N", "ALL",
        )
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str) -> dict[str, object]:
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
                    "attempts": attempt,
                    "rows": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = OUT / "raw" / f"{sha256(series_key.encode())[:16]}.raw"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": series_key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
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
                "frequency": row.get("FREQ"),
                "reference_area": row.get("REF_AREA"),
                "counterpart_area": row.get("COUNTERPART_AREA"),
                "reference_sector": row.get("REF_SECTOR"),
                "counterpart_sector": row.get("COUNTERPART_SECTOR"),
                "measure": row.get("STO"),
                "entry": row.get("ACCOUNTING_ENTRY"),
                "international_item": row.get("INT_ACC_ITEM"),
                "functional_category": row.get("FCT_BREAKDOWN"),
                "instrument": row.get("INSTR_ASSET"),
                "maturity": row.get("MATURITY"),
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "currency_denominator": row.get("CURRENCY_DENOM"),
                "valuation": row.get("VALUATION"),
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def usable_value(
    series: dict[str, object],
    measure: str,
    maturity: str,
    unit: str,
) -> float | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if not rows:
        return None
    for row in rows:
        if (
            row.get("reference_area") not in {None, "RO"}
            or row.get("counterpart_area") not in {None, "W1"}
            or row.get("entry") not in {None, "A"}
            or row.get("international_item") not in {None, "FA"}
            or row.get("functional_category") not in {None, "O"}
            or row.get("instrument") not in {None, "F2"}
            or row.get("maturity") not in {None, maturity}
            or row.get("unit") not in {None, unit}
        ):
            return None

    mapping = {str(row["period"]): float(row["value"]) for row in rows}
    if measure == "LE":
        value = mapping.get("2025-Q4")
        return value if value is not None and math.isfinite(value) else None
    periods = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    if not all(p in mapping and math.isfinite(mapping[p]) for p in periods):
        return None
    return sum(mapping[p] for p in periods)


def sector_value(
    values: dict[tuple[str, str, str, str], float | None],
    sector: str,
    measure: str,
    unit: str,
) -> tuple[float | None, str]:
    direct = values[(sector, measure, unit, "T")]
    if direct is not None:
        return direct, "DIRECT_ALL_MATURITY"
    short = values[(sector, measure, unit, "S")]
    long = values[(sector, measure, unit, "L")]
    if short is not None and long is not None:
        return short + long, "EXACT_S_PLUS_L"
    return None, "UNAVAILABLE"


def check_identity(
    name: str,
    total: tuple[float | None, str],
    parts: list[tuple[float | None, str]],
) -> dict[str, object]:
    total_value, total_source = total
    if total_value is None or any(value is None for value, _ in parts):
        return {
            "identity": name,
            "status": "COVERAGE_INCOMPLETE",
            "total": total_value,
            "total_source": total_source,
            "part_values": [value for value, _ in parts],
            "part_sources": [source for _, source in parts],
            "residual": None,
        }
    part_sum = sum(float(value) for value, _ in parts)
    residual = part_sum - float(total_value)
    return {
        "identity": name,
        "status": "PASS" if abs(residual) <= TOL else "FAIL",
        "total": total_value,
        "total_source": total_source,
        "part_sum": part_sum,
        "part_values": [value for value, _ in parts],
        "part_sources": [source for _, source in parts],
        "residual": residual,
    }


def main() -> None:
    specs = [
        (sector, measure, unit, maturity)
        for sector in SECTORS
        for measure in MEASURES
        for unit in UNITS
        for maturity in MATURITIES
    ]
    series_by_spec = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch, key(sector, measure, maturity, unit)):
            (sector, measure, unit, maturity)
            for sector, measure, unit, maturity in specs
        }
        for index, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            series_by_spec[spec] = future.result()
            print(f"[{index}/{len(futures)}] {spec}", flush=True)

    values = {}
    for spec, series in series_by_spec.items():
        sector, measure, unit, maturity = spec
        values[spec] = usable_value(series, measure, maturity, unit)

    availability = []
    for sector in SECTORS:
        for measure in MEASURES:
            for unit in UNITS:
                value, source = sector_value(values, sector, measure, unit)
                availability.append(
                    {
                        "sector": sector,
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        "value": value,
                        "coverage": source,
                        "direct_maturity_availability": {
                            maturity: values[(sector, measure, unit, maturity)] is not None
                            for maturity in MATURITIES
                        },
                    }
                )

    identities = []
    for measure in MEASURES:
        for unit in UNITS:
            get = lambda sector: sector_value(values, sector, measure, unit)
            identities.extend(
                [
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S1 = S121 + S12T + S13 + S1P",
                            get("S1"),
                            [get("S121"), get("S12T"), get("S13"), get("S1P")],
                        ),
                    },
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S1 = S121 + S12T + S13 + S124 + S12Q + S12O + S11 + S1M",
                            get("S1"),
                            [
                                get("S121"), get("S12T"), get("S13"), get("S124"),
                                get("S12Q"), get("S12O"), get("S11"), get("S1M"),
                            ],
                        ),
                    },
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S12T = S122 + S123",
                            get("S12T"),
                            [get("S122"), get("S123")],
                        ),
                    },
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S1P = S12M + S1V",
                            get("S1P"),
                            [get("S12M"), get("S1V")],
                        ),
                    },
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S12M = S124 + S12Q + S12O",
                            get("S12M"),
                            [get("S124"), get("S12Q"), get("S12O")],
                        ),
                    },
                    {
                        "measure": "stock" if measure == "LE" else "flow_2025",
                        "unit": unit,
                        **check_identity(
                            "S1V = S11 + S1M",
                            get("S1V"),
                            [get("S11"), get("S1M")],
                        ),
                    },
                ]
            )

    mapping = []
    for measure in MEASURES:
        for unit in UNITS:
            get = lambda sector: sector_value(values, sector, measure, unit)
            bnr = get("S121")
            gov = get("S13")
            corp = get("S11")
            hh = get("S1M")
            mfi = get("S12T")
            other_fin = get("S12M")
            financial = (
                None
                if mfi[0] is None or other_fin[0] is None
                else float(mfi[0]) + float(other_fin[0])
            )
            exact = all(
                item[0] is not None
                for item in (bnr, gov, corp, hh, mfi, other_fin)
            )
            mapping.append(
                {
                    "measure": "stock" if measure == "LE" else "flow_2025",
                    "unit": unit,
                    "BNR_S121": bnr,
                    "G_S13": gov,
                    "C_S11": corp,
                    "H_S1M": hh,
                    "F_S12T_plus_S12M": {
                        "value": financial,
                        "S12T": mfi,
                        "S12M": other_fin,
                    },
                    "exact_RMD_sector_mapping_available": exact,
                }
            )

    status_counts = {}
    for series in series_by_spec.values():
        status = str(series.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1

    report = {
        "audit_version": "0.1",
        "phase": "BPS/BOP external F2 sector-structure audit",
        "benchmark_changed": False,
        "F21_materialization_allowed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "series_requested": len(specs),
        "series_status_counts": status_counts,
        "network_errors_present": any(
            series.get("status") == "NETWORK_ERROR"
            for series in series_by_spec.values()
        ),
        "availability": availability,
        "sector_identity_checks": identities,
        "rmd_mapping_candidates": mapping,
        "rule": (
            "Source-structure audit only. A coarse BPS S1P value cannot be split "
            "into S12M/S11/S1M unless the official detailed components are published "
            "or an exact independently controlled identity makes the split unique."
        ),
        "conceptual_warning": (
            "BPS follows BPM6 external-sector conventions. Its F2 currency-and-deposits "
            "series is not presumed definitionally identical to QSA ESA F2; a separate "
            "concept bridge is required before Accounting Spine use."
        ),
    }
    (OUT / "bps_f2_sector_structure_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_requested": report["series_requested"],
                "series_status_counts": status_counts,
                "network_errors_present": report["network_errors_present"],
                "rmd_mapping_candidates": mapping,
                "sector_identity_checks": identities,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
