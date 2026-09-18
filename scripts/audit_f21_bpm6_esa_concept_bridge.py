from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("F21_CONCEPT_BRIDGE_OUT", "f21_concept_bridge_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/bop_iip6_q"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub BPM6 ESA F2 concept bridge)"
PERIOD = "2025-Q4"
SECTOR_TOL = 1.5
AGG_TOL = 3.5
RMD_SECTORS = ("H", "C", "F", "G", "BNR")
EUROSTAT_SECTORS = ("S1M", "S11", "S12T", "S12M", "S13", "S121", "S1")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def eurostat_url(
    bop_item: str,
    sector: str,
    sectpart: str,
    currency: str,
) -> str:
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": "Q",
            "currency": currency,
            "bop_item": bop_item,
            "sector10": sector,
            "sectpart": sectpart,
            "stk_flow": "A_LE",
            "partner": "WRL_REST",
            "geo": "RO",
            "sinceTimePeriod": PERIOD,
            "untilTimePeriod": PERIOD,
        }
    )
    return f"{API}?{query}"


def fetch_item(
    bop_item: str,
    sector: str,
    sectpart: str,
    currency: str,
) -> dict[str, object]:
    url = eurostat_url(bop_item, sector, sectpart, currency)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
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
                    "bop_item": bop_item,
                    "sector": sector,
                    "sectpart": sectpart,
                    "currency": currency,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "value": None,
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_name = hashlib.sha256(
        f"{bop_item}|{sector}|{sectpart}|{currency}".encode()
    ).hexdigest()[:16] + ".json"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "bop_item": bop_item,
        "sector": sector,
        "sectpart": sectpart,
        "currency": currency,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "content_type": headers.get("Content-Type"),
        "value": None,
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        result["response_preview"] = body[:500].decode("utf-8", errors="replace")
        return result

    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    if payload.get("class") != "dataset":
        result["status"] = "UNEXPECTED_PAYLOAD"
        result["payload_keys"] = sorted(payload.keys())
        return result

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes):
        result["status"] = "UNEXPECTED_DIMENSIONS"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    zero_dimensions = [
        dim for dim, size in zip(ids, sizes) if int(size) == 0
    ]
    if zero_dimensions:
        result["status"] = "FILTER_VALUE_NOT_IN_DATASET_CONSTRAINT"
        result["ids"] = ids
        result["sizes"] = sizes
        result["zero_dimensions"] = zero_dimensions
        return result

    if any(int(size) != 1 for dim, size in zip(ids, sizes) if dim != "time"):
        result["status"] = "UNEXPECTED_DIMENSIONS"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    time_index = (
        payload.get("dimension", {})
        .get("time", {})
        .get("category", {})
        .get("index", {})
    )
    if isinstance(time_index, list):
        times = list(time_index)
    else:
        times = [
            k for k, _ in sorted(time_index.items(), key=lambda item: int(item[1]))
        ]
    if PERIOD not in times:
        result["status"] = "NO_OBSERVATION"
        result["available_time_codes"] = times
        return result

    pos = times.index(PERIOD)
    values = payload.get("value", {})
    if isinstance(values, list):
        raw_value = values[pos] if pos < len(values) else None
    elif isinstance(values, dict):
        raw_value = values.get(str(pos))
        if raw_value is None:
            raw_value = values.get(pos)
    else:
        raw_value = None

    if raw_value is None:
        result["status"] = "NO_OBSERVATION"
        return result

    try:
        result["value"] = float(raw_value)
    except (TypeError, ValueError):
        result["status"] = "NON_NUMERIC_OBSERVATION"
        result["raw_value"] = raw_value
        return result

    result["status"] = "AVAILABLE"
    result["dataset_updated"] = payload.get("updated")
    return result


def choose_reserve(
    results: dict[tuple[str, str, str, str], dict],
    currency: str,
) -> dict:
    candidates = []
    for sector, sectpart in (
        ("S121", "S1"),
        ("S1", "S1"),
        ("S121", "S1N"),
        ("S1", "S1N"),
    ):
        item = results[("FA__R__F2", sector, sectpart, currency)]
        if item.get("value") is not None:
            candidates.append(item)

    if not candidates:
        return {"status": "UNAVAILABLE", "value": None, "candidate_count": 0}

    values = [float(x["value"]) for x in candidates]
    if max(values) - min(values) > SECTOR_TOL:
        return {
            "status": "CONFLICTING_AVAILABLE_REPRESENTATIONS",
            "value": None,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    preferred = next(
        (
            x
            for x in candidates
            if x["sector"] == "S121" and x["sectpart"] == "S1"
        ),
        candidates[0],
    )
    return {
        "status": "AVAILABLE",
        "value": float(preferred["value"]),
        "selected": {
            "sector": preferred["sector"],
            "sectpart": preferred["sectpart"],
            "currency": preferred["currency"],
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def direct_f2_sector_values(
    results: dict[tuple[str, str, str, str], dict],
    currency: str,
) -> dict[str, float | None]:
    values = {}
    for sector in EUROSTAT_SECTORS:
        item = results[("FA__D__F2", sector, "S1", currency)]
        values[sector] = (
            None if item.get("value") is None else float(item["value"])
        )
    return values


def main() -> None:
    eurostat = json.loads(
        (
            ROOT
            / "model"
            / "accounting"
            / "eurostat_f2_sector_detail_assessment.json"
        ).read_text(encoding="utf-8")
    )
    qsa_f2m = json.loads(
        (
            ROOT
            / "model"
            / "accounting"
            / "f2m_component_2025.json"
        ).read_text(encoding="utf-8")
    )
    qsa_controls = json.loads(
        (
            ROOT
            / "model"
            / "accounting"
            / "f21_f2_external_bridge_assessment.json"
        ).read_text(encoding="utf-8")
    )

    specs: list[tuple[str, str, str, str]] = []

    # Reserve-assets F2 probes.
    for sector in ("S121", "S1"):
        for sectpart in ("S1", "S1N"):
            for currency in ("MIO_NAC", "MIO_EUR"):
                specs.append(("FA__R__F2", sector, sectpart, currency))

    # Direct-investment F2 subinstrument probes. These are required to establish
    # functional-category completeness; absence is not interpreted as zero.
    for sector in EUROSTAT_SECTORS:
        for currency in ("MIO_NAC", "MIO_EUR"):
            specs.append(("FA__D__F2", sector, "S1", currency))

    # Composite direct-investment debt instruments are diagnostic only. They
    # explicitly cannot substitute for F2 because FL contains multiple debt
    # instruments.
    for sector in ("S1", "S11", "S1M", "S12T", "S12M", "S13", "S121"):
        specs.append(("FA__D__FL", sector, "S1", "MIO_NAC"))

    results: dict[tuple[str, str, str, str], dict] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_item, *spec): spec for spec in specs
        }
        for i, future in enumerate(as_completed(futures), start=1):
            spec = futures[future]
            results[spec] = future.result()
            print(
                f"[{i}/{len(futures)}] {spec}: {results[spec]['status']}",
                flush=True,
            )

    reserve_nac = choose_reserve(results, "MIO_NAC")
    reserve_eur = choose_reserve(results, "MIO_EUR")
    direct_nac = direct_f2_sector_values(results, "MIO_NAC")
    direct_eur = direct_f2_sector_values(results, "MIO_EUR")

    direct_required = ("S1M", "S11", "S12T", "S12M", "S13", "S121")
    direct_f2_detail_complete_nac = all(
        direct_nac[sector] is not None for sector in direct_required
    )
    direct_f2_total_available_nac = direct_nac["S1"] is not None

    direct_debt_diagnostic = {
        sector: {
            "status": results[("FA__D__FL", sector, "S1", "MIO_NAC")]["status"],
            "value": results[("FA__D__FL", sector, "S1", "MIO_NAC")].get("value"),
            "use": "DIAGNOSTIC_ONLY_NOT_F2_SUBSTITUTE",
        }
        for sector in ("S1", "S11", "S1M", "S12T", "S12M", "S13", "S121")
    }

    oi = eurostat["stock_MIO_NAC"]
    other_investment = {
        "H": float(oi["households_NPISH_S1M"]),
        "C": float(oi["nonfinancial_corporations_S11"]),
        "G": float(oi["government_S13"]),
        "F": float(oi["MFI_S12T"]) + float(oi["other_financial_S12M"]),
        "BNR": float(oi["BNR_S121"]),
    }

    f2m_external = {}
    for cell in qsa_f2m["matrices"]["stock"]:
        if cell["issuer"] == "X" and cell["holder"] in RMD_SECTORS:
            if cell["value"] is None:
                raise RuntimeError(
                    f"Missing materialized external F2M cell: {cell}"
                )
            f2m_external[cell["holder"]] = float(cell["value"])
    if set(f2m_external) != set(RMD_SECTORS):
        raise RuntimeError("Incomplete materialized external F2M holder set")

    direct_rmd = None
    if direct_f2_detail_complete_nac:
        direct_rmd = {
            "H": float(direct_nac["S1M"]),
            "C": float(direct_nac["S11"]),
            "G": float(direct_nac["S13"]),
            "F": float(direct_nac["S12T"]) + float(direct_nac["S12M"]),
            "BNR": float(direct_nac["S121"]),
        }

    functional_category_complete = (
        direct_f2_detail_complete_nac
        and reserve_nac.get("status") == "AVAILABLE"
    )

    sector_bridge = []
    reserve_value = reserve_nac.get("value")
    for sector in RMD_SECTORS:
        known_components = {
            "BPM6_other_investment_F2_million_RON":
                other_investment[sector]
        }
        if sector == "BNR" and reserve_value is not None:
            known_components["BPM6_reserve_assets_F2_million_RON"] = float(
                reserve_value
            )
        if direct_rmd is not None:
            known_components[
                "BPM6_direct_investment_F2_million_RON"
            ] = direct_rmd[sector]

        known_subtotal = sum(known_components.values())

        if not functional_category_complete:
            candidate_total = None
            implied_f21 = None
            status = "FUNCTIONAL_CATEGORY_F2_COVERAGE_INCOMPLETE"
        else:
            candidate_total = known_subtotal
            implied_f21 = candidate_total - f2m_external[sector]
            status = (
                "PASS_NONNEGATIVE_WITHIN_SOURCE_PRECISION"
                if implied_f21 >= -SECTOR_TOL
                else "FAIL_NEGATIVE_IMPLIED_F21"
            )

        sector_bridge.append(
            {
                "sector": sector,
                "known_BPM6_F2_components_subtotal_million_RON":
                    known_subtotal,
                "known_components": known_components,
                "functional_category_F2_coverage_complete":
                    functional_category_complete,
                "candidate_BPM6_total_external_F2_million_RON":
                    candidate_total,
                "materialized_QSA_external_F2M_million_RON":
                    f2m_external[sector],
                "implied_external_F21_million_RON": implied_f21,
                "status": status,
            }
        )

    qsa_total_f2 = float(
        qsa_controls["aggregate_QSA_controls"]["stock"][
            "published_W1_total_F2_million_RON"
        ]
    )
    qsa_total_f21 = float(
        qsa_controls["aggregate_QSA_controls"]["stock"][
            "published_W1_total_F21_million_RON"
        ]
    )

    known_components_sum = sum(
        float(x["known_BPM6_F2_components_subtotal_million_RON"])
        for x in sector_bridge
    )
    known_components_gap_to_qsa_f2 = known_components_sum - qsa_total_f2

    if functional_category_complete:
        sum_f2 = sum(
            float(x["candidate_BPM6_total_external_F2_million_RON"])
            for x in sector_bridge
        )
        sum_f21 = sum(
            float(x["implied_external_F21_million_RON"])
            for x in sector_bridge
        )
        f2_residual = sum_f2 - qsa_total_f2
        f21_residual = sum_f21 - qsa_total_f21
        f2_status = "PASS" if abs(f2_residual) <= AGG_TOL else "FAIL"
        f21_status = "PASS" if abs(f21_residual) <= AGG_TOL else "FAIL"
    else:
        sum_f2 = sum_f21 = f2_residual = f21_residual = None
        f2_status = f21_status = "FUNCTIONAL_CATEGORY_COVERAGE_BLOCKED"

    sector_level_pass = functional_category_complete and all(
        x["status"] == "PASS_NONNEGATIVE_WITHIN_SOURCE_PRECISION"
        for x in sector_bridge
    )
    aggregate_pass = f2_status == "PASS" and f21_status == "PASS"
    network_errors = any(
        x.get("status") == "NETWORK_ERROR" for x in results.values()
    )
    bridge_pass = (
        functional_category_complete
        and not network_errors
        and sector_level_pass
        and aggregate_pass
    )

    status_counts: dict[str, int] = {}
    for item in results.values():
        status = str(item["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    report = {
        "audit_version": "0.2",
        "phase": "BPM6-to-ESA F2 concept bridge",
        "benchmark_changed": False,
        "F21_materialization_allowed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "official_concept_rule": (
            "ESA F2 corresponds across BPM6 functional categories. "
            "Other Investment F2 is residual and cannot be treated as full F2 "
            "without testing Direct Investment F2 and Reserve Assets F2."
        ),
        "series_status_counts": status_counts,
        "reserve_asset_F2_probe": {
            "MIO_NAC": reserve_nac,
            "MIO_EUR": reserve_eur,
        },
        "direct_investment_F2_probe": {
            "MIO_NAC": direct_nac,
            "MIO_EUR": direct_eur,
            "required_sector_detail_complete_MIO_NAC":
                direct_f2_detail_complete_nac,
            "total_S1_available_MIO_NAC":
                direct_f2_total_available_nac,
        },
        "direct_investment_debt_FL_diagnostic":
            direct_debt_diagnostic,
        "functional_category_F2_coverage_complete":
            functional_category_complete,
        "sector_bridge": sector_bridge,
        "known_components_diagnostic": {
            "known_BPM6_F2_components_sum_million_RON":
                known_components_sum,
            "published_QSA_W1_F2_million_RON": qsa_total_f2,
            "known_components_minus_QSA_F2_million_RON":
                known_components_gap_to_qsa_f2,
            "interpretation": (
                "Diagnostic only when functional-category F2 coverage is "
                "incomplete; the residual must not be allocated."
            ),
        },
        "aggregate_controls": {
            "candidate_BPM6_sector_sum_F2_million_RON": sum_f2,
            "published_QSA_W1_F2_million_RON": qsa_total_f2,
            "F2_residual_million_RON": f2_residual,
            "F2_status": f2_status,
            "candidate_implied_F21_sum_million_RON": sum_f21,
            "published_QSA_W1_F21_million_RON": qsa_total_f21,
            "F21_residual_million_RON": f21_residual,
            "F21_status": f21_status,
            "aggregate_tolerance_million_RON": AGG_TOL,
        },
        "sector_level_pass": sector_level_pass,
        "aggregate_pass": aggregate_pass,
        "network_errors_present": network_errors,
        "concept_bridge_pass": bridge_pass,
        "promotion_status": (
            "BPM6_ESA_F2_CONCEPT_BRIDGE_ELIGIBLE_FOR_LATER_MATERIALIZATION"
            if bridge_pass
            else "BPM6_ESA_F2_CONCEPT_BRIDGE_BLOCKED"
        ),
        "rule": (
            "Missing Direct-Investment F2 subinstrument detail is not zero. "
            "Composite FA__D__FL debt instruments cannot substitute for F2. "
            "No functional-category gap may be clipped or redistributed."
        ),
    }
    (OUT / "f21_bpm6_esa_concept_bridge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_status_counts": status_counts,
                "reserve_MIO_NAC": reserve_nac,
                "direct_investment_F2_probe_MIO_NAC": direct_nac,
                "direct_investment_F2_detail_complete":
                    direct_f2_detail_complete_nac,
                "functional_category_F2_coverage_complete":
                    functional_category_complete,
                "known_components_diagnostic":
                    report["known_components_diagnostic"],
                "sector_bridge": sector_bridge,
                "aggregate_controls": report["aggregate_controls"],
                "concept_bridge_pass": bridge_pass,
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
